"""Outbound dial floor: Today queues + call disposition (CRM Dial patterns)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine.crm_helpers import _now
from porterchain_api.crm_models import CrmLead, CrmSalesTask
from porterchain_api.domain.crm_states import LeadDecisionStatus, LeadStatus

CALL_OUTCOMES = (
    "no_answer",
    "voicemail",
    "busy",
    "gatekeeper",
    "callback",
    "send_info",
    "interested",
    "quote_requested",
    "connected_qualified",
    "not_interested",
    "wrong_number",
    "dnc",
)

OUTCOME_STATUS: dict[str, str] = {
    "no_answer": LeadStatus.CONTACTED.value,
    "voicemail": LeadStatus.CONTACTED.value,
    "busy": LeadStatus.CONTACTED.value,
    "gatekeeper": LeadStatus.CONTACTED.value,
    "callback": LeadStatus.CONTACTED.value,
    "send_info": LeadStatus.NURTURING.value,
    "interested": LeadStatus.QUALIFIED.value,
    "quote_requested": LeadStatus.QUALIFIED.value,
    "connected_qualified": LeadStatus.QUALIFIED.value,
    "not_interested": LeadStatus.UNQUALIFIED.value,
    "wrong_number": LeadStatus.UNQUALIFIED.value,
    "dnc": LeadStatus.UNQUALIFIED.value,
}

OUTCOME_DEFAULTS: dict[str, dict[str, Any]] = {
    "no_answer": {"next_action": "Call", "follow_up_days": 1},
    "voicemail": {"next_action": "Call", "follow_up_days": 2},
    "busy": {"next_action": "Call", "follow_up_days": 1},
    "gatekeeper": {"next_action": "Call", "follow_up_days": 2},
    "callback": {"next_action": "Call", "follow_up_days": 1},
    "send_info": {"next_action": "Send information", "follow_up_days": 3},
    "interested": {"next_action": "Follow up", "follow_up_days": 1},
    "quote_requested": {"next_action": "Prepare quote", "follow_up_days": 1},
    "connected_qualified": {"next_action": "Prepare quote", "follow_up_days": 1},
    "not_interested": {"next_action": "No action", "follow_up_days": None},
    "wrong_number": {"next_action": "No action", "follow_up_days": None},
    "dnc": {"next_action": "No action", "follow_up_days": None},
}

_VENDOR_SOURCE = "vendor_import"
_CRM_SOURCE = "crm_import"
_OUTBOUND_SOURCES = (_VENDOR_SOURCE, _CRM_SOURCE)
_LOSS_OUTCOMES = frozenset({"not_interested", "wrong_number", "dnc"})


def _has_phone(lead: CrmLead) -> bool:
    return bool((lead.phone or "").strip())


def today_queues(db: Session, *, limit: int | None = None) -> dict[str, Any]:
    """Ready / Follow-ups / Interested packs for outbound dial floor (full lists).

    Includes leads with and without phone so the dial UI can filter contact
    completeness client-side.
    """
    not_noise = ~cast(CrmLead.tags, String).ilike("%noise%")

    ready_q = (
        db.query(CrmLead)
        .filter(
            CrmLead.source.in_(_OUTBOUND_SOURCES),
            CrmLead.status == LeadStatus.NEW.value,
            CrmLead.priority == "high",
            not_noise,
        )
        .order_by(CrmLead.lead_score.desc(), CrmLead.created_at.desc())
    )
    if limit is not None:
        ready_q = ready_q.limit(limit)
    ready = ready_q.all()

    now = datetime.now(UTC)
    due_ids = (
        db.query(CrmSalesTask.entity_id)
        .filter(
            CrmSalesTask.entity_type == "lead",
            CrmSalesTask.task_type == "call",
            CrmSalesTask.status == "open",
            CrmSalesTask.due_at.isnot(None),
            CrmSalesTask.due_at <= now,
        )
    )
    followups_q = (
        db.query(CrmLead)
        .filter(CrmLead.id.in_(due_ids))
        .order_by(CrmLead.last_touch_at.asc().nullsfirst())
    )
    if limit is not None:
        followups_q = followups_q.limit(limit)
    followups = followups_q.all()

    interested_q = (
        db.query(CrmLead)
        .filter(
            CrmLead.source.in_(_OUTBOUND_SOURCES),
            or_(
                CrmLead.status == LeadStatus.QUALIFIED.value,
                CrmLead.decision_status == LeadDecisionStatus.READY_TO_CONVERT.value,
            ),
            not_noise,
        )
        .order_by(CrmLead.updated_at.desc())
    )
    if limit is not None:
        interested_q = interested_q.limit(limit)
    interested = interested_q.all()

    def pack(rows: list[CrmLead]) -> list[dict[str, Any]]:
        return [
            {
                "id": r.id,
                "company_name": r.company_name,
                "phone": r.phone,
                "email": r.email,
                "primary_contact_name": r.primary_contact_name,
                "has_phone": _has_phone(r),
                "city": (r.address or {}).get("city") if isinstance(r.address, dict) else None,
                "priority": r.priority,
                "status": r.status,
                "lead_score": r.lead_score,
                "service_area": r.service_area,
                "agent_status": (
                    ((r.custom_fields or {}).get("lead_agent") or {}).get("status")
                    if isinstance(r.custom_fields, dict)
                    else None
                ),
                "needs_enrich": "needs_enrich" in (r.tags or [])
                or (
                    isinstance(r.custom_fields, dict)
                    and ((r.custom_fields.get("lead_agent") or {}).get("status") == "needs_enrich")
                ),
            }
            for r in rows
        ]

    ready_pack = pack(ready)
    followups_pack = pack(followups)
    interested_pack = pack(interested)

    def contact_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
        with_phone = sum(1 for r in rows if r.get("has_phone"))
        return {
            "total": len(rows),
            "with_phone": with_phone,
            "without_phone": len(rows) - with_phone,
        }

    return {
        "ready": ready_pack,
        "followups": followups_pack,
        "interested": interested_pack,
        "counts": {
            "ready": len(ready_pack),
            "followups": len(followups_pack),
            "interested": len(interested_pack),
            "ready_contact": contact_counts(ready_pack),
            "followups_contact": contact_counts(followups_pack),
            "interested_contact": contact_counts(interested_pack),
        },
    }


def next_lead_in_queue(
    db: Session,
    *,
    after_id: str | None,
    queue: str = "ready",
) -> str | None:
    packs = today_queues(db)
    key = "ready" if queue not in ("ready", "followups", "interested") else queue
    ids = [row["id"] for row in packs[key]]
    if not ids:
        return None
    if not after_id or after_id not in ids:
        return ids[0]
    idx = ids.index(after_id)
    if idx + 1 < len(ids):
        return ids[idx + 1]
    return None


def apply_call_disposition(
    db: Session,
    crm: Any,
    *,
    lead: CrmLead,
    outcome: str,
    notes: str | None = None,
    loss_reason: str | None = None,
    next_action: str | None = None,
    follow_up_at: datetime | None = None,
    actor_id: str | None = None,
    queue: str = "ready",
    contact_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    consent_marketing: bool | None = None,
) -> dict[str, Any]:
    if outcome not in CALL_OUTCOMES:
        raise ValueError("invalid_outcome")
    if outcome in _LOSS_OUTCOMES and not (loss_reason or "").strip():
        raise ValueError("loss_reason_required")

    defaults = OUTCOME_DEFAULTS.get(outcome) or {}
    status = OUTCOME_STATUS[outcome]
    patch: dict[str, Any] = {"status": status, "last_touch_at": _now()}
    if contact_name:
        patch["primary_contact_name"] = contact_name.strip()[:255]
    if email:
        patch["email"] = email.strip().lower()[:320]
    if phone:
        from porterchain_api.collaboration_engine.lead_ingest_service import normalize_phone_e164

        norm = normalize_phone_e164(phone)
        if norm:
            patch["phone"] = norm[:32]
    if consent_marketing is True:
        consent = dict(lead.consent or {})
        consent["marketing"] = True
        consent["marketing_at"] = _now().isoformat()
        consent["marketing_source"] = "call_disposition"
        patch["consent"] = consent
    if outcome in ("interested", "quote_requested", "connected_qualified"):
        patch["decision_status"] = LeadDecisionStatus.READY_TO_CONVERT.value
    if outcome == "dnc":
        patch["decision_status"] = LeadDecisionStatus.LOST.value

    lead = crm.update_lead(db, lead.id, patch)

    if outcome == "dnc":
        from porterchain_api.collaboration_engine.lead_suppression import upsert_suppression

        upsert_suppression(
            db,
            email=lead.email,
            phone=lead.phone,
            source="call_dnc",
            lead_id=lead.id,
        )

    action = next_action if next_action is not None else defaults.get("next_action")
    due = follow_up_at
    if due is None and defaults.get("follow_up_days") is not None:
        due = _now() + timedelta(days=int(defaults["follow_up_days"]))

    task_id = None
    if due and action and action != "No action":
        task = CrmSalesTask(
            title=f"{action}: {lead.company_name}",
            description=notes or f"Outcome: {outcome}",
            task_type="call",
            status="open",
            priority=lead.priority or "medium",
            entity_type="lead",
            entity_id=lead.id,
            assigned_to=lead.assigned_to or actor_id,
            due_at=due,
            created_by=actor_id,
        )
        db.add(task)
        db.flush()
        task_id = task.id

    body = notes or ""
    if loss_reason:
        body = f"{body}\nLoss reason: {loss_reason}".strip()
    crm.log_activity(
        db,
        entity_type="lead",
        entity_id=lead.id,
        activity_type="call",
        subject=f"Call: {outcome}",
        body=body or None,
        actor_id=actor_id,
        metadata={
            "outcome": outcome,
            "next_action": action,
            "loss_reason": loss_reason,
            "follow_up_at": due.isoformat() if due else None,
        },
    )
    db.commit()
    db.refresh(lead)

    return {
        "lead": lead,
        "outcome": outcome,
        "status": lead.status,
        "task_id": task_id,
        "next_lead_id": next_lead_in_queue(db, after_id=lead.id, queue=queue),
    }
