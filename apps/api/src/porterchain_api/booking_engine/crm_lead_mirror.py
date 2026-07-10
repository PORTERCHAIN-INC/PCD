"""Mirror retail booking funnel contacts into CRM leads for admin visibility."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.models import Quote
from porterchain_api.collaboration_engine import CrmSalesService
from porterchain_api.crm_models import CrmLead
from porterchain_api.db_json import json_text
from porterchain_api.domain.crm_states import LeadPriority, LeadStatus

_crm = CrmSalesService()


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
    existing = (
        db.query(CrmLead)
        .filter(quote_id_expr == quote_id)
        .first()
    )
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

    return _crm.create_lead(
        db,
        None,
        {
            "company_name": str(company_name)[:255],
            "primary_contact_name": email.split("@", 1)[0],
            "email": email,
            "phone": phone,
            "source": "website_booking",
            "status": LeadStatus.NEW.value,
            "priority": LeadPriority.HIGH.value,
            "internal_notes": f"Retail booking started — stage: {stage}",
            "custom_fields": {
                "quote_id": quote_id,
                "customer_id": customer_id,
                "stage": stage,
                "vehicle_class": quote.vehicle_class if quote else None,
                "amount_cents": quote.amount_cents if quote else None,
                "pickup": pickup,
                "dropoff": dropoff,
                "form": "booking",
            },
            "tags": ["booking", stage],
        },
    )
