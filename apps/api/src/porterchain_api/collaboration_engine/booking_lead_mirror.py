"""Mirror retail booking funnel contacts into CRM leads for admin visibility.

Owns CrmLead writes for the website booking path (§3.2.6 collaboration ownership).
"""

from __future__ import annotations

from typing import Any

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
    company_name = (
        pickup.get("formatted_address")
        or pickup.get("address")
        or f"Retail booking ({quote.vehicle_class or 'delivery'})"
        if quote
        else "Retail booking"
    )

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
