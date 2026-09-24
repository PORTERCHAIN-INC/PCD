"""Mirror retail booking funnel contacts into CRM leads for admin visibility."""

from __future__ import annotations

from sqlalchemy.orm import Session

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


def mirror_booking_lead_to_crm(
    db: Session,
    *,
    email: str,
    phone: str | None,
    quote_id: str,
    customer_id: str,
    stage: str,
) -> CrmLead | None:
    """Best-effort CRM lead for website booking — idempotent per quote_id."""
    quote_id_expr = json_text(CrmLead.custom_fields, "quote_id")
    existing = db.query(CrmLead).filter(quote_id_expr == quote_id).first()
    if existing:
        return existing

    quote = db.get(Quote, quote_id)
    pickup = (quote.pickup or {}) if quote else {}
    dropoff = (quote.dropoff or {}) if quote else {}
    company_name = (
        pickup.get("formatted_address")
        or pickup.get("address")
        or f"Retail booking ({quote.vehicle_class or 'delivery'})"
        if quote
        else "Retail booking"
    )

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
            custom_fields={
                "quote_id": quote_id,
                "customer_id": customer_id,
                "stage": stage,
                "vehicle_class": quote.vehicle_class if quote else None,
                "amount_cents": quote.amount_cents if quote else None,
                "pickup": pickup,
                "dropoff": dropoff,
                "form": "booking",
            },
            seed_conversation=False,
        ),
    )
    if result.lead is not None and quote_id and not result.lead.quote_id:
        result.lead.quote_id = quote_id
    return result.lead
