"""Apply Lead Assist accept/reject decisions (admin CRM)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine.crm_service import CrmSalesService
from porterchain_api.crm_models import CrmConversation, CrmConversationMessage, CrmLead, CrmSalesTask


class LeadAssistBlocked(Exception):
    """Raised when an accepted proposal cannot be applied (e.g. nurture blocked)."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def apply_lead_assist_decision(
    db: Session,
    crm: CrmSalesService,
    lead: CrmLead,
    *,
    lead_id: str,
    proposal_id: str,
    decision: str,
    draft_reply: str | None,
    decision_status: str | None,
    actor_id: str,
) -> dict[str, Any]:
    """Apply accept|reject for a Lead Assist proposal and log activity."""
    applied: dict[str, Any] = {"proposal_id": proposal_id, "decision": decision}
    if decision == "accept":
        patch: dict[str, Any] = {}
        pid = (proposal_id or "").strip()
        if pid in ("draft_reply", "decision_status") or decision_status or draft_reply:
            if decision_status or pid == "decision_status":
                status_val = decision_status or None
                if status_val:
                    patch["decision_status"] = status_val
            if draft_reply or pid == "draft_reply":
                reply = (draft_reply or "").strip()
                if reply:
                    notes = (lead.internal_notes or "").strip()
                    patch["internal_notes"] = (
                        f"{notes}\n[Assist draft] {reply}".strip()
                        if notes
                        else f"[Assist draft] {reply}"
                    )
                    convo = (
                        db.query(CrmConversation)
                        .filter(
                            CrmConversation.lead_id == lead_id,
                            CrmConversation.status == "open",
                        )
                        .order_by(CrmConversation.updated_at.desc())
                        .first()
                    )
                    if convo:
                        db.add(
                            CrmConversationMessage(
                                conversation_id=convo.id,
                                direction="outbound",
                                body=reply,
                                actor_type="staff",
                                actor_id=actor_id,
                                metadata_json={
                                    "from_assist": True,
                                    "proposal_id": proposal_id,
                                },
                            )
                        )
        if pid == "send_nurture_intro":
            from porterchain_api.collaboration_engine.lead_nurture import (
                enqueue_nurture_intro_email,
            )
            from porterchain_api.config import get_settings

            settings = get_settings()
            website = getattr(settings, "website_url", "") or ""
            sent = enqueue_nurture_intro_email(lead, website_url=website, db=db)
            applied["nurture_intro_enqueued"] = bool(sent)
            if not sent:
                raise LeadAssistBlocked("nurture_intro_blocked")
        if pid == "schedule_call":
            due = datetime.now(UTC) + timedelta(days=1)
            db.add(
                CrmSalesTask(
                    title=f"Assist call: {lead.company_name}",
                    description="Created from Lead Assist schedule_call proposal",
                    task_type="call",
                    status="open",
                    priority="medium",
                    entity_type="lead",
                    entity_id=lead.id,
                    due_at=due,
                    created_by=actor_id,
                )
            )
            applied["call_task_scheduled"] = True
        if patch:
            lead = crm.update_lead(db, lead_id, patch)
        applied["lead_id"] = lead.id
        applied["decision_status"] = lead.decision_status
        db.commit()
    crm.log_activity(
        db,
        entity_type="lead",
        entity_id=lead_id,
        activity_type="note",
        subject=f"Assist {decision}: {proposal_id}",
        body=draft_reply if decision == "accept" else None,
        actor_id=actor_id,
        metadata={
            "from_assist": True,
            "assist_decision": decision,
            "proposal_id": proposal_id,
        },
    )
    return {"ok": True, **applied}


__all__ = ["LeadAssistBlocked", "apply_lead_assist_decision"]
