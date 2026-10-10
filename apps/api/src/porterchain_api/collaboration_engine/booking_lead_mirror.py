"""Mirror retail booking funnel contacts into CRM leads for admin visibility.

Owns CrmLead writes for the website booking path (§3.2.6 collaboration ownership).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.booking_draft_models import BookingDraft
from porterchain_api.booking_models import Quote
from porterchain_api.collaboration_engine.lead_ingest_service import (
    CanonicalLeadEvent,
    LeadIngestService,
)
from porterchain_api.crm_models import CrmLead
from porterchain_api.db_json import json_text
from porterchain_api.domain.crm_states import (
    LeadIntentType,
    LeadPriority,
    LeadSourceChannel,
    LeadStatus,
)

_PROVIDER = "porterchain"
_ingest = LeadIngestService()


def _consent_from_booking(consent: dict[str, Any] | None) -> dict[str, Any]:
    """Map retail booking consent onto CrmLead.consent nurture keys."""
    from porterchain_api.collaboration_engine.lead_consent import casl_evidence

    return casl_evidence(consent, source="website_booking", actor="lead")


def _apply_spine(
    lead: CrmLead,
    *,
    quote_id: str,
    visitor_session_id: str | None,
    booking_draft_id: str | None,
    consent: dict[str, Any] | None,
) -> None:
    if quote_id and not getattr(lead, "quote_id", None):
        lead.quote_id = quote_id
    if visitor_session_id and not getattr(lead, "visitor_session_id", None):
        lead.visitor_session_id = visitor_session_id[:64]
        raw_fields = getattr(lead, "custom_fields", None)
        fields = dict(raw_fields) if isinstance(raw_fields, dict) else {}
        fields.setdefault("visitor_id", visitor_session_id[:64])
        lead.custom_fields = fields
    if booking_draft_id and not getattr(lead, "booking_draft_id", None):
        lead.booking_draft_id = booking_draft_id[:36]
    merged = _consent_from_booking(consent)
    if merged:
        c = dict(getattr(lead, "consent", None) or {})
        c.update(merged)
        lead.consent = c


def _retail_display_name(db: Session, *, customer_id: str | None, email: str) -> str:
    """Retail lead label: the customer's name, else their email — never an address."""
    from porterchain_api.booking_models import Customer

    customer = db.get(Customer, customer_id) if customer_id else None
    name = (getattr(customer, "full_name", None) or "").strip()
    if name:
        return name[:255]
    return (email or "Retail customer").strip()[:255]


def mark_booking_lead_converted(
    db: Session,
    *,
    quote_id: str,
    order_id: str,
    customer_id: str | None = None,
    email: str | None = None,
) -> CrmLead | None:
    """Paid website booking → CRM lead converted + linked to the order. Flush only.

    Idempotent; also repairs the legacy pickup-address company name.
    """
    from porterchain_api.collaboration_engine.crm_helpers import _now
    from porterchain_api.domain.crm_states import LeadDecisionStatus

    quote_id_expr = json_text(CrmLead.custom_fields, "quote_id")
    lead = (
        db.query(CrmLead)
        .filter((CrmLead.quote_id == quote_id) | (quote_id_expr == quote_id))
        .first()
    )
    if lead is None and (email or "").strip():
        # Quoted/replied sales lead who booked through the link → that lead is Won.
        lead = (
            db.query(CrmLead)
            .filter(
                func.lower(CrmLead.email) == email.strip().lower(),
                CrmLead.status.in_(("new", "replied", "quoted")),
            )
            .order_by(CrmLead.created_at.desc())
            .first()
        )
    if lead is None:
        return None
    now = _now()
    from porterchain_api.collaboration_engine.lead_pipeline import mark_won

    mark_won(lead, order_id=order_id)
    lead.order_id = order_id
    lead.status = LeadStatus.WON.value
    lead.decision_status = LeadDecisionStatus.CONVERTED.value
    lead.awaiting_reply = False
    lead.sla_first_response_due_at = None
    lead.last_touch_at = now
    fields = dict(lead.custom_fields or {})
    fields["stage"] = "paid"
    fields["order_id"] = order_id
    pickup_label = None
    pickup = fields.get("pickup")
    if isinstance(pickup, dict):
        pickup_label = pickup.get("formatted_address") or pickup.get("address")
    if (
        not lead.company_name
        or lead.company_name == pickup_label
        or str(lead.company_name).startswith("Retail booking")
    ):
        lead.company_name = _retail_display_name(
            db, customer_id=customer_id or fields.get("customer_id"), email=email or lead.email or ""
        )
    lead.custom_fields = fields
    tags = [t for t in (lead.tags or []) if t != "booking_started"]
    if "paid" not in tags:
        tags.append("paid")
    lead.tags = tags
    db.flush()
    return lead


def mirror_booking_lead_to_crm(
    db: Session,
    *,
    email: str,
    phone: str | None,
    quote_id: str,
    customer_id: str,
    stage: str,
    visitor_session_id: str | None = None,
    consent: dict[str, Any] | None = None,
) -> CrmLead | None:
    """Best-effort CRM lead for website booking — idempotent per quote_id."""
    quote = db.get(Quote, quote_id)
    draft = (
        db.query(BookingDraft).filter(BookingDraft.quote_id == quote_id).first()
        if quote_id
        else None
    )
    visitor_key = (
        (visitor_session_id or "").strip()
        or (getattr(quote, "visitor_session_id", None) or "").strip()
        or (getattr(draft, "session_id", None) or "").strip()
        or None
    )
    if visitor_key:
        visitor_key = visitor_key[:64]
    draft_id = draft.id if draft else None

    quote_id_expr = json_text(CrmLead.custom_fields, "quote_id")
    existing = (
        db.query(CrmLead)
        .filter((CrmLead.quote_id == quote_id) | (quote_id_expr == quote_id))
        .first()
    )
    if existing:
        _apply_spine(
            existing,
            quote_id=quote_id,
            visitor_session_id=visitor_key,
            booking_draft_id=draft_id,
            consent=consent or (quote.consent if quote else None),
        )
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    pickup = (quote.pickup or {}) if quote else {}
    dropoff = (quote.dropoff or {}) if quote else {}
    company_name = _retail_display_name(db, customer_id=customer_id, email=email)

    external_ids: dict[str, str] = {}
    if visitor_key:
        external_ids["visitor_session"] = visitor_key

    custom_fields: dict[str, Any] = {
        "quote_id": quote_id,
        "customer_id": customer_id,
        "stage": stage,
        "vehicle_class": quote.vehicle_class if quote else None,
        "amount_cents": quote.amount_cents if quote else None,
        "pickup": pickup,
        "dropoff": dropoff,
        "form": "booking",
        "visitor_id": visitor_key,
        "booking_draft_id": draft_id,
    }

    result = _ingest.ingest(
        db,
        CanonicalLeadEvent(
            channel=LeadSourceChannel.WEBSITE_BOOKING.value,
            source="website_booking",
            provider=_PROVIDER,
            external_event_id=quote_id,
            company_name=str(company_name)[:255],
            primary_contact_name=email.split("@", 1)[0],
            email=email,
            phone=phone,
            intent_type=LeadIntentType.RETAIL_CUSTOMER.value,
            priority=LeadPriority.HIGH.value,
            status=LeadStatus.NEW.value,
            message=f"Retail booking started — stage: {stage}",
            tags=["booking", stage],
            custom_fields={k: v for k, v in custom_fields.items() if v is not None},
            consent=_consent_from_booking(consent or (quote.consent if quote else None)),
            external_ids=external_ids,
            seed_conversation=False,
        ),
    )
    lead = result.lead
    if lead is not None:
        _apply_spine(
            lead,
            quote_id=quote_id,
            visitor_session_id=visitor_key,
            booking_draft_id=draft_id,
            consent=None,  # already merged via ingest
        )
        # ingest() already commits; refresh spine if we mutated after.
        if (
            getattr(lead, "quote_id", None) != quote_id
            or getattr(lead, "visitor_session_id", None)
            or getattr(lead, "booking_draft_id", None)
        ):
            db.add(lead)
            db.commit()
            db.refresh(lead)
    return lead
