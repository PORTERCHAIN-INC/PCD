from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from porterchain_api.auth.clerk_webhook_service import ClerkWebhookService
from porterchain_api.booking_engine.stripe_webhook_service import StripeWebhookService
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.driver_engine.background_check_service import DriverBackgroundCheckService
from porterchain_api.services.stripe_service import StripeSignatureError, construct_webhook_event

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
_stripe_webhooks = StripeWebhookService()
_clerk_webhooks = ClerkWebhookService()
_background_checks = DriverBackgroundCheckService()


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="stripe_webhook_not_configured")

    try:
        event = construct_webhook_event(payload, sig_header, settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_payload") from exc
    except StripeSignatureError as exc:
        raise HTTPException(status_code=400, detail="invalid_signature") from exc

    return _stripe_webhooks.handle(db, settings, event)


@router.post("/clerk")
async def clerk_webhook(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    """Clerk user lifecycle webhooks (Svix-signed). Idempotent; no operational cascade deletes."""
    payload = await request.body()
    return _clerk_webhooks.handle(
        db,
        settings,
        payload=payload,
        svix_id=request.headers.get("svix-id"),
        svix_timestamp=request.headers.get("svix-timestamp"),
        svix_signature=request.headers.get("svix-signature"),
    )


@router.post("/checkr")
async def checkr_webhook(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    """Checkr report/invitation webhooks → driver background_check_status."""
    import json

    from porterchain_api.db import db_transaction

    payload = await request.body()
    signature = request.headers.get("X-Checkr-Signature") or request.headers.get("Checkr-Signature")
    try:
        event = json.loads(payload.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid_payload") from exc
    if not isinstance(event, dict):
        raise HTTPException(status_code=400, detail="invalid_payload")
    try:
        with db_transaction(db):
            return _background_checks.handle_webhook(
                db,
                settings,
                payload=payload,
                signature=signature,
                event=event,
            )
    except PermissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
