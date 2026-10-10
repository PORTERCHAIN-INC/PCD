"""Public newsletter sign-up — double opt-in subscriber list (not sales leads)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.routers.public_ingest_auth import verify_public_ingest_key
from porterchain_api.schemas_public import (
    NewsletterConfirmRequest,
    NewsletterConfirmResponse,
    NewsletterSubscribeRequest,
    NewsletterSubscribeResponse,
)

router = APIRouter(prefix="/v1/public", tags=["public"])


@router.post(
    "/newsletter/subscribe", response_model=NewsletterSubscribeResponse, status_code=202
)
def newsletter_subscribe(
    body: NewsletterSubscribeRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_ingest_key: Annotated[str | None, Header(alias="X-Ingest-Key")] = None,
) -> NewsletterSubscribeResponse:
    """Double opt-in: store pending + send one confirmation email."""
    verify_public_ingest_key(settings, x_ingest_key)
    from porterchain_api.marketing_site.form_guard import client_ip, guard_public_form
    from porterchain_api.collaboration_engine.newsletter_subscribers import subscribe

    if guard_public_form(
        request,
        db,
        bucket="newsletter",
        app_env=settings.app_env,
        honeypot=body.website,
        form_elapsed_ms=body.form_elapsed_ms,
    ):
        return NewsletterSubscribeResponse()
    try:
        subscribe(
            db,
            email=body.email,
            website_url=getattr(settings, "website_url", "") or "",
            source_page=body.source_page,
            locale=body.locale,
            ip=client_ip(request),
            attribution={
                "utm_source": body.utm_source,
                "utm_medium": body.utm_medium,
                "utm_campaign": body.utm_campaign,
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return NewsletterSubscribeResponse()


@router.post("/newsletter/confirm", response_model=NewsletterConfirmResponse)
def newsletter_confirm(
    body: NewsletterConfirmRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> NewsletterConfirmResponse:
    from porterchain_api.marketing_site.form_guard import client_ip
    from porterchain_api.collaboration_engine.newsletter_subscribers import confirm

    row = confirm(db, token=body.token, ip=client_ip(request))
    if row is None:
        raise HTTPException(status_code=400, detail="invalid_or_expired_token")
    return NewsletterConfirmResponse(status="confirmed")
