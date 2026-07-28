"""Public website inquiry ingest — creates CRM leads."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine import CrmSalesService
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.crm_states import LeadPriority, LeadStatus
from porterchain_api.routers.public_ingest_auth import verify_public_ingest_key
from porterchain_api.schemas_public import PublicInquiryCreate, PublicInquiryResponse

router = APIRouter(prefix="/v1/public", tags=["public"])
_crm = CrmSalesService()


def _priority_for_intent(
    intent: str | None,
    *,
    inquiry_type: str | None = None,
    form: str | None = None,
) -> str:
    if intent in ("quote", "demo", "driver_partner"):
        return LeadPriority.HIGH.value
    if form in ("business", "vehicle_partner"):
        return LeadPriority.HIGH.value
    if inquiry_type == "newsletter" or form == "newsletter":
        return LeadPriority.LOW.value
    return LeadPriority.MEDIUM.value


def _source_label(body: PublicInquiryCreate) -> str:
    form = (body.form or "").strip()
    source_page = (body.source_page or "").strip().lower()
    if form == "vehicle_partner":
        return "website_driver_partner"
    if form == "business":
        return "website_business"
    if form == "newsletter":
        return "website_newsletter"
    if body.inquiry_type == "partnership" and (
        "vehicle-partner" in source_page or source_page.endswith("/drive")
    ):
        return "website_driver_partner"
    if body.intent == "quote":
        return "website_quote"
    if body.intent == "demo":
        return "website_demo"
    if form == "contact":
        return "website_contact"
    return "website_contact"


@router.post("/inquiries", response_model=PublicInquiryResponse, status_code=201)
def create_public_inquiry(
    body: PublicInquiryCreate,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_ingest_key: Annotated[str | None, Header(alias="X-Ingest-Key")] = None,
) -> PublicInquiryResponse:
    verify_public_ingest_key(settings, x_ingest_key)

    email = body.email.strip()
    if not email:
        raise HTTPException(status_code=422, detail="email_required")

    contact_name = (body.name or "").strip() or email.split("@", 1)[0]
    company_name = (body.business_name or "").strip() or contact_name

    phone_raw = (body.phone or "").strip() or None
    phone = phone_raw[:32] if phone_raw else None

    custom_fields = {
        k: v
        for k, v in {
            "intent": body.intent,
            "inquiry_type": body.inquiry_type,
            "message": body.message,
            "source_page": body.source_page,
            "form": body.form,
            "utm_source": body.utm_source,
            "utm_campaign": body.utm_campaign,
            "utm_medium": body.utm_medium,
            **({"phone_full": phone_raw} if phone_raw and phone_raw != phone else {}),
        }.items()
        if v
    }

    lead = _crm.create_lead(
        db,
        None,
        {
            "company_name": company_name,
            "primary_contact_name": contact_name,
            "email": email,
            "phone": phone,
            "source": _source_label(body),
            "status": LeadStatus.NEW.value,
            "priority": _priority_for_intent(
                body.intent,
                inquiry_type=body.inquiry_type,
                form=body.form,
            ),
            "internal_notes": (body.message or "").strip() or None,
            "custom_fields": custom_fields,
            "tags": [t for t in [body.intent, body.inquiry_type] if t],
        },
    )
    return PublicInquiryResponse(id=lead.id)
