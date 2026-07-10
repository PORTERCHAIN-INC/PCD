"""Public website inquiry ingest — creates CRM leads."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine import CrmSalesService
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.crm_states import LeadPriority, LeadStatus
from porterchain_api.schemas_public import PublicInquiryCreate, PublicInquiryResponse

router = APIRouter(prefix="/v1/public", tags=["public"])
_crm = CrmSalesService()


def _verify_ingest_key(
    settings: Settings,
    x_ingest_key: str | None,
) -> None:
    key = settings.public_ingest_api_key.strip()
    if not key:
        if settings.app_env == "local":
            return
        raise HTTPException(status_code=503, detail="ingest_not_configured")
    if x_ingest_key != key:
        raise HTTPException(status_code=401, detail="invalid_ingest_key")


def _priority_for_intent(intent: str | None) -> str:
    if intent in ("quote", "demo"):
        return LeadPriority.HIGH.value
    return LeadPriority.MEDIUM.value


def _source_label(body: PublicInquiryCreate) -> str:
    if body.form == "business":
        return "website_business"
    if body.intent == "quote":
        return "website_quote"
    if body.intent == "demo":
        return "website_demo"
    return "website_contact"


@router.post("/inquiries", response_model=PublicInquiryResponse, status_code=201)
def create_public_inquiry(
    body: PublicInquiryCreate,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_ingest_key: Annotated[str | None, Header(alias="X-Ingest-Key")] = None,
) -> PublicInquiryResponse:
    _verify_ingest_key(settings, x_ingest_key)

    email = body.email.strip()
    if not email:
        raise HTTPException(status_code=422, detail="email_required")

    contact_name = (body.name or "").strip() or email.split("@", 1)[0]
    company_name = (body.business_name or "").strip() or contact_name

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
            "phone": (body.phone or "").strip() or None,
            "source": _source_label(body),
            "status": LeadStatus.NEW.value,
            "priority": _priority_for_intent(body.intent),
            "internal_notes": (body.message or "").strip() or None,
            "custom_fields": custom_fields,
            "tags": [t for t in [body.intent, body.inquiry_type] if t],
        },
    )
    return PublicInquiryResponse(id=lead.id)
