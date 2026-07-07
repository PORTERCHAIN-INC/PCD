import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from porterchain_api.booking_engine.stripe_webhook_service import StripeWebhookService
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.fleetbase_engine.webhook_ingress_service import WebhookIngressService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
_stripe_webhooks = StripeWebhookService()
_fleetbase_ingress = WebhookIngressService()


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
        event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_payload") from exc
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail="invalid_signature") from exc

    return _stripe_webhooks.handle(db, settings, event)


@router.post("/fleetbase")
async def fleetbase_webhook(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    payload = await request.body()
    signature = request.headers.get("X-Fleetbase-Signature") or request.headers.get("X-Signature")
    try:
        return _fleetbase_ingress.accept(db, settings, raw_body=payload, signature=signature)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
