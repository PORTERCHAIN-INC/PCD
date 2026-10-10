"""Public website inquiry ingest — creates CRM leads via Lead Ingest Bus."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from porterchain_api.booking_engine.visitor_tracking_service import (
    VisitorTrackingService,
)
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
from pydantic import BaseModel, Field

from porterchain_api.schemas_public import (
    PublicInquiryCreate,
    PublicInquiryResponse,
)

# Contact-form inquiry types that are buying signals (→ high priority + alert).
SALES_INQUIRY_TYPES = frozenset({"sales", "quote", "pricing", "enterprise", "demo", "business"})


class LeadUnsubscribeRequest(BaseModel):
    token: str = Field(min_length=8, max_length=512)


class LeadUnsubscribeResponse(BaseModel):
    status: str = "unsubscribed"
    lead_id: str | None = None

router = APIRouter(prefix="/v1/public", tags=["public"])
_ingest = LeadIngestService()
_visitors = VisitorTrackingService()


def _priority_for_intent(
    intent: str | None,
    *,
    inquiry_type: str | None = None,
    form: str | None = None,
) -> str:
    if intent in ("quote", "demo", "driver_partner"):
        return LeadPriority.HIGH.value
    if (inquiry_type or "").strip().lower() in SALES_INQUIRY_TYPES:
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


def _consent_snapshot(body: PublicInquiryCreate, *, ip: str | None) -> dict[str, Any]:
    """CASL evidence from the form's own checkbox — never from the cookie banner."""
    from porterchain_api.collaboration_engine.lead_consent import (
        casl_evidence,
        form_consent_evidence,
    )

    source = f"website_{(body.form or 'contact').strip().lower()[:40]}"
    if body.marketing_consent is not None or body.contact_consent is not None:
        return form_consent_evidence(
            marketing=bool(body.marketing_consent),
            source=source,
            ip=ip,
            locale=body.locale,
            page=body.source_page,
            contact_consent=body.contact_consent,
        )
    # Legacy clients: casl_evidence strips CMP (cookie banner) marketing flags.
    return casl_evidence(dict(body.consent or {}), source=source, actor="lead")


def _is_newsletter(body: PublicInquiryCreate) -> bool:
    return body.form == "newsletter" or body.inquiry_type == "newsletter"

@router.post("/inquiries", response_model=PublicInquiryResponse, status_code=201)
def create_public_inquiry(
    body: PublicInquiryCreate,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_ingest_key: Annotated[str | None, Header(alias="X-Ingest-Key")] = None,
) -> PublicInquiryResponse:
    verify_public_ingest_key(settings, x_ingest_key)
    from porterchain_api.marketing_site.form_guard import client_ip, guard_public_form

    if guard_public_form(
        request,
        db,
        bucket="inquiry",
        app_env=settings.app_env,
        honeypot=body.website,
        form_elapsed_ms=body.form_elapsed_ms,
    ):
        # Same answer as a real submission; nothing stored.
        return PublicInquiryResponse(id=str(uuid.uuid4()))
    ip = client_ip(request)

    email = body.email.strip()
    if not email:
        raise HTTPException(status_code=422, detail="email_required")

    if _is_newsletter(body):
        # Newsletter sign-ups are subscribers (double opt-in), not sales leads.
        from porterchain_api.collaboration_engine.newsletter_subscribers import subscribe

        try:
            sub = subscribe(
                db,
                email=email,
                website_url=getattr(settings, "website_url", "") or "",
                source_page=body.source_page,
                locale=body.locale,
                ip=ip,
                attribution={
                    "utm_source": body.utm_source,
                    "utm_medium": body.utm_medium,
                    "utm_campaign": body.utm_campaign,
                },
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return PublicInquiryResponse(id=sub.id, status="pending_confirmation")

    contact_name = (body.name or "").strip() or email.split("@", 1)[0]
    company_name = (body.business_name or "").strip() or contact_name
    phone_raw = (body.phone or "").strip() or None
    source = _source_label(body)

    visitor_key = (body.visitor_id or "").strip() or None
    if visitor_key:
        visitor_key = visitor_key[:64]
        _visitors.ensure_session(
            db,
            session_id=visitor_key,
            utm_source=body.utm_source,
            utm_medium=body.utm_medium,
            utm_campaign=body.utm_campaign,
            signals={
                "intent": body.intent,
                "form": body.form,
                "source_page": body.source_page or "/",
                "from_page": "public_inquiry",
            },
        )

    custom_fields = {
        k: v
        for k, v in {
            "intent": body.intent,
            "inquiry_type": body.inquiry_type,
            "message": body.message,
            "source_page": body.source_page,
            "form": body.form,
            "visitor_id": visitor_key,
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

    external_ids: dict[str, str] = {}
    if visitor_key:
        external_ids["visitor_session"] = visitor_key

    consent = _consent_snapshot(body, ip=ip)

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
            consent=consent,
            attribution={
                k: v
                for k, v in {
                    "utm_source": body.utm_source,
                    "utm_campaign": body.utm_campaign,
                    "utm_medium": body.utm_medium,
                    "utm_term": body.utm_term,
                    "utm_content": body.utm_content,
                    "referred_by_merchant_id": referred_by,
                }.items()
                if v
            },
            referred_by_merchant_id=referred_by,
            external_ids=external_ids,
            seed_conversation=bool((body.message or "").strip()),
        ),
    )
    return PublicInquiryResponse(id=result.lead.id)


@router.post("/leads/unsubscribe", response_model=LeadUnsubscribeResponse)
def unsubscribe_lead(
    body: LeadUnsubscribeRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LeadUnsubscribeResponse:
    """CASL commercial-email unsubscribe via signed nurture token (no ingest key)."""
    from porterchain_api.collaboration_engine.lead_consent import (
        commit_unsubscribe,
        verify_unsubscribe_token,
    )
    from porterchain_api.crm_models import CrmLead

    secret = (settings.jwt_secret or settings.public_ingest_api_key or "").strip()
    lead_id = verify_unsubscribe_token(token=body.token, secret=secret)
    if not lead_id:
        raise HTTPException(status_code=400, detail="invalid_or_expired_token")
    lead = db.get(CrmLead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead_not_found")
    commit_unsubscribe(db, lead)
    return LeadUnsubscribeResponse(status="unsubscribed", lead_id=lead.id)


class LeadEngagementRequest(BaseModel):
    """ESP open/click callback — signed nurture token or X-Ingest-Key."""

    token: str | None = Field(default=None, max_length=512)
    lead_id: str | None = Field(default=None, max_length=36)
    kind: str = Field(description="open | click")
    campaign: str | None = Field(default=None, max_length=120)


class LeadEngagementResponse(BaseModel):
    status: str = "ok"
    lead_id: str
    kind: str
    lead_score: int


@router.post("/leads/engagement", response_model=LeadEngagementResponse)
def lead_engagement(
    body: LeadEngagementRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_ingest_key: Annotated[str | None, Header(alias="X-Ingest-Key")] = None,
) -> LeadEngagementResponse:
    """Record ESP open/click and bump lead score (capped)."""
    from porterchain_api.collaboration_engine.lead_consent import (
        verify_unsubscribe_token,
    )
    from porterchain_api.collaboration_engine.lead_engagement import (
        record_email_engagement,
    )
    from porterchain_api.crm_models import CrmLead

    kind = (body.kind or "").strip().lower()
    if kind not in ("open", "click"):
        raise HTTPException(status_code=422, detail="kind_must_be_open_or_click")

    lead_id: str | None = None
    if body.token:
        secret = (settings.jwt_secret or settings.public_ingest_api_key or "").strip()
        lead_id = verify_unsubscribe_token(token=body.token, secret=secret)
        if not lead_id:
            raise HTTPException(status_code=400, detail="invalid_or_expired_token")
    else:
        verify_public_ingest_key(settings, x_ingest_key)
        lead_id = (body.lead_id or "").strip() or None
        if not lead_id:
            raise HTTPException(status_code=422, detail="lead_id_required")

    lead = db.get(CrmLead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead_not_found")
    out = record_email_engagement(
        db, lead, kind=kind, campaign=body.campaign, actor="esp"  # type: ignore[arg-type]
    )
    return LeadEngagementResponse(
        lead_id=out["lead_id"], kind=kind, lead_score=int(out["lead_score"])
    )
