"""Public website inquiry ingest — creates CRM leads via Lead Ingest Bus."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine.lead_ingest_service import (
    CanonicalLeadEvent,
    LeadIngestService,
)
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.crm_states import (
    LeadIntentType,
    LeadPriority,
    LeadSourceChannel,
    LeadStatus,
)
from porterchain_api.routers.public_ingest_auth import verify_public_ingest_key
from porterchain_api.schemas_public import PublicInquiryCreate, PublicInquiryResponse

router = APIRouter(prefix="/v1/public", tags=["public"])
_ingest = LeadIngestService()


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


def _intent_type(body: PublicInquiryCreate, source: str) -> str:
    if source == "website_driver_partner" or body.intent == "driver_partner":
        return LeadIntentType.DRIVER_PARTNER.value
    if body.form == "newsletter":
        return LeadIntentType.UNKNOWN.value
    if body.form in ("business",) or body.intent in ("quote", "demo"):
        return LeadIntentType.MERCHANT.value
    return LeadIntentType.MERCHANT.value


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
    source = _source_label(body)

    custom_fields = {
        k: v
        for k, v in {
            "intent": body.intent,
            "inquiry_type": body.inquiry_type,
            "message": body.message,
            "source_page": body.source_page,
            "form": body.form,
            **({"phone_full": phone_raw} if phone_raw else {}),
        }.items()
        if v
    }

    referred_by = (body.referred_by_merchant_id or "").strip() or None
    channel = (
        LeadSourceChannel.MERCHANT_REFERRAL.value
        if referred_by
        else LeadSourceChannel.WEBSITE.value
    )
    if referred_by:
        source = "merchant_referral"
        custom_fields["referred_by_merchant_id"] = referred_by

    result = _ingest.ingest(
        db,
        CanonicalLeadEvent(
            channel=channel,
            source=source,
            provider="website_public_inquiry",
            external_event_id=f"inq:{email.lower()}:{uuid.uuid4()}",
            company_name=company_name,
            primary_contact_name=contact_name,
            email=email,
            phone=phone_raw,
            intent_type=_intent_type(body, source),
            priority=_priority_for_intent(
                body.intent,
                inquiry_type=body.inquiry_type,
                form=body.form,
            ),
            status=LeadStatus.NEW.value,
            message=(body.message or "").strip() or None,
            tags=[t for t in [body.intent, body.inquiry_type, "referral" if referred_by else None] if t],
            custom_fields=custom_fields,
            attribution={
                k: v
                for k, v in {
                    "utm_source": body.utm_source,
                    "utm_campaign": body.utm_campaign,
                    "utm_medium": body.utm_medium,
                    "referred_by_merchant_id": referred_by,
                }.items()
                if v
            },
            referred_by_merchant_id=referred_by,
            seed_conversation=bool((body.message or "").strip()),
        ),
    )
    return PublicInquiryResponse(id=result.lead.id)
