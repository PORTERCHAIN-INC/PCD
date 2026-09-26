"""Lead 360 — compose CrmLead hub with visitor, retail, and commerce panels."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import AdminUser
from porterchain_api.booking_draft_abandon import ABANDONED_AFTER_MINUTES, is_abandoned
from porterchain_api.booking_draft_models import BookingDraft
from porterchain_api.booking_models import AbandonedCheckout, Lead, Quote
from porterchain_api.collaboration_engine.crm_service import CrmSalesService
from porterchain_api.crm_models import (
    CrmConversation,
    CrmLead,
    CrmLeadIdentity,
    CrmReferralCredit,
)
from porterchain_api.platform import visitor_insight


_TASK_LIMIT = 50
_ACTIVITY_LIMIT = 50
_DRAFT_LIMIT = 20
_ABANDONED_LIMIT = 20
_QUOTE_LIMIT = 20
_CONVO_LIMIT = 20
_IDENTITY_LIMIT = 20


class Lead360Service:
    def __init__(self) -> None:
        self._crm = CrmSalesService()

    def get(self, db: Session, lead_id: str) -> dict[str, Any] | None:
        lead = self._crm.get_lead(db, lead_id)
        if not lead:
            return None

        now = datetime.now(UTC)
        retail = (
            db.query(Lead).filter(Lead.crm_lead_id == lead.id).order_by(Lead.created_at.desc()).first()
        )
        identities = (
            db.query(CrmLeadIdentity)
            .filter(CrmLeadIdentity.lead_id == lead.id)
            .limit(_IDENTITY_LIMIT)
            .all()
        )
        conversations = (
            db.query(CrmConversation)
            .filter(CrmConversation.lead_id == lead.id)
            .order_by(CrmConversation.updated_at.desc())
            .limit(_CONVO_LIMIT)
            .all()
        )
        tasks = self._crm.list_tasks(
            db, entity_type="lead", entity_id=lead.id, limit=_TASK_LIMIT
        )
        activities = self._crm.list_activities(
            db, entity_type="lead", entity_id=lead.id, limit=_ACTIVITY_LIMIT
        )
        visitor = visitor_insight.insight_for_lead(db, lead) or {}

        quote_ids = self._quote_ids(lead, retail)
        quotes = []
        if quote_ids:
            quotes = (
                db.query(Quote)
                .filter(Quote.id.in_(quote_ids))
                .order_by(Quote.created_at.desc())
                .limit(_QUOTE_LIMIT)
                .all()
            )

        drafts = self._drafts_for_lead(db, lead, quote_ids)
        draft_rows = [self._draft_row(d, now) for d in drafts]

        abandoned = []
        if quote_ids:
            abandoned = (
                db.query(AbandonedCheckout)
                .filter(AbandonedCheckout.quote_id.in_(quote_ids))
                .order_by(AbandonedCheckout.created_at.desc())
                .limit(_ABANDONED_LIMIT)
                .all()
            )

        referral = (
            db.query(CrmReferralCredit)
            .filter(CrmReferralCredit.lead_id == lead.id)
            .order_by(CrmReferralCredit.created_at.desc())
            .first()
        )

        assignee = self._assignee(db, lead.assigned_to)
        score = self._score_breakdown(lead)
        nurture_tags = [t for t in (lead.tags or []) if "nurture" in str(t).lower()]
        from porterchain_api.collaboration_engine.lead_suppression import is_suppressed
        from porterchain_api.collaboration_engine.lead_whatsapp_gate import whatsapp_outbound_status

        do_not_contact = is_suppressed(db, email=lead.email, phone=lead.phone)
        whatsapp_status = whatsapp_outbound_status(lead)
        urgent_tasks = [
            t
            for t in tasks
            if t.status == "open"
            and t.task_type in ("follow_up", "call", "todo")
            and (t.priority == "high" or "unassigned" in (t.title or "").lower())
        ]

        sla_breached = bool(
            lead.sla_first_response_due_at
            and lead.sla_first_response_due_at < now
            and lead.status == "new"
        )

        return {
            "lead": lead,
            "retail_lead": (
                {
                    "id": retail.id,
                    "email": retail.email,
                    "phone": retail.phone,
                    "quote_id": retail.quote_id,
                    "customer_id": retail.customer_id,
                    "crm_lead_id": retail.crm_lead_id,
                    "stage": retail.stage,
                    "source": retail.source,
                    "created_at": retail.created_at,
                }
                if retail
                else None
            ),
            "identities": [
                {
                    "id": r.id,
                    "kind": r.kind,
                    "value": r.value_normalized,
                    "raw": r.raw_value,
                }
                for r in identities
            ],
            "conversations": [
                {
                    "id": c.id,
                    "channel": c.channel,
                    "status": c.status,
                    "updated_at": c.updated_at,
                }
                for c in conversations
            ],
            "tasks": tasks,
            "nurture": {
                "tags": nurture_tags,
                "open_task_ids": [
                    t.id
                    for t in tasks
                    if t.status == "open" and "nurture" in (t.title or "").lower()
                ],
                "marketing_consent": bool((lead.consent or {}).get("marketing")),
                "do_not_contact": do_not_contact,
                "whatsapp": whatsapp_status,
            },
            "activities": [self._crm.activity_dict(a) for a in activities],
            "visitor": visitor,
            "quotes": [
                {
                    "id": q.id,
                    "state": q.state,
                    "amount_cents": q.amount_cents,
                    "vehicle_class": q.vehicle_class,
                    "visitor_session_id": q.visitor_session_id,
                    "created_at": q.created_at,
                }
                for q in quotes
            ],
            "drafts": draft_rows,
            # Stripe / session-expired abandoned — NOT the same as draft inactivity.
            "abandoned_checkouts": [
                {
                    "id": a.id,
                    "quote_id": a.quote_id,
                    "email": a.email,
                    "reason": a.reason,
                    "created_at": a.created_at,
                    "kind": "stripe_abandoned_checkout",
                }
                for a in abandoned
            ],
            "referral": (
                {
                    "id": referral.id,
                    "referring_merchant_id": referral.referring_merchant_id,
                    "amount_cents": referral.amount_cents,
                    "status": referral.status,
                    "created_at": referral.created_at,
                }
                if referral
                else None
            ),
            "sla": {
                "first_response_due_at": lead.sla_first_response_due_at,
                "breached": sla_breached,
            },
            "assignee": assignee,
            "consent": lead.consent or {},
            "score": score,
            "merge_candidate_of": lead.merge_candidate_of,
            "urgent_unassigned_tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "task_type": t.task_type,
                    "priority": getattr(t, "priority", None),
                    "due_at": t.due_at,
                }
                for t in urgent_tasks[:5]
            ],
            "linked_merchant_id": None,  # filled post-convert via company; P2 UI
            "linked_customer_id": retail.customer_id if retail else None,
            "linked_driver_id": None,
            "last_capi": (lead.custom_fields or {}).get("_capi")
            if isinstance(lead.custom_fields, dict)
            else None,
        }

    @staticmethod
    def _quote_ids(lead: CrmLead, retail: Lead | None) -> list[str]:
        ids: list[str] = []
        if lead.quote_id:
            ids.append(lead.quote_id)
        if retail and retail.quote_id and retail.quote_id not in ids:
            ids.append(retail.quote_id)
        fields = lead.custom_fields if isinstance(lead.custom_fields, dict) else {}
        cf = fields.get("quote_id")
        if isinstance(cf, str) and cf.strip() and cf not in ids:
            ids.append(cf.strip())
        return ids[:_QUOTE_LIMIT]

    def _drafts_for_lead(
        self, db: Session, lead: CrmLead, quote_ids: list[str]
    ) -> list[BookingDraft]:
        drafts: list[BookingDraft] = []
        seen: set[str] = set()
        if lead.booking_draft_id:
            d = db.get(BookingDraft, lead.booking_draft_id)
            if d:
                drafts.append(d)
                seen.add(d.id)
        if lead.visitor_session_id:
            for d in (
                db.query(BookingDraft)
                .filter(BookingDraft.session_id == lead.visitor_session_id)
                .order_by(BookingDraft.updated_at.desc())
                .limit(_DRAFT_LIMIT)
                .all()
            ):
                if d.id not in seen:
                    drafts.append(d)
                    seen.add(d.id)
        if quote_ids:
            for d in (
                db.query(BookingDraft)
                .filter(BookingDraft.quote_id.in_(quote_ids))
                .order_by(BookingDraft.updated_at.desc())
                .limit(_DRAFT_LIMIT)
                .all()
            ):
                if d.id not in seen:
                    drafts.append(d)
                    seen.add(d.id)
        return drafts[:_DRAFT_LIMIT]

    @staticmethod
    def _draft_row(draft: BookingDraft, now: datetime) -> dict[str, Any]:
        abandoned = is_abandoned(draft, now)
        return {
            "id": draft.id,
            "session_id": draft.session_id,
            "quote_id": draft.quote_id,
            "state": draft.state,
            "current_step": draft.current_step,
            "amount_cents": draft.amount_cents,
            "updated_at": draft.updated_at,
            # Distinct from AbandonedCheckout — inactivity at a funnel step.
            "draft_abandoned": abandoned,
            "draft_abandoned_reason": (
                f"inactive_{ABANDONED_AFTER_MINUTES}m" if abandoned else None
            ),
            "kind": "booking_draft",
        }

    @staticmethod
    def _assignee(db: Session, assigned_to: str | None) -> dict[str, Any] | None:
        if not assigned_to:
            return None
        admin = db.get(AdminUser, assigned_to)
        if not admin:
            return {"id": assigned_to, "name": None, "email": None}
        return {
            "id": admin.id,
            "name": admin.name,
            "email": admin.email,
        }

    @staticmethod
    def _score_breakdown(lead: CrmLead) -> dict[str, Any]:
        fields = lead.custom_fields if isinstance(lead.custom_fields, dict) else {}
        raw = fields.get("_score") if isinstance(fields.get("_score"), dict) else {}
        return {
            "lead_score": lead.lead_score,
            "heuristic": raw.get("heuristic"),
            "predictive": raw.get("predictive"),
            "method": raw.get("method"),
            "priors_n": raw.get("priors_n"),
        }


__all__ = ["Lead360Service"]
