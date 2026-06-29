import json

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from porterchain_api.booking_engine import BookingConfirmationService, BookingService, PaymentService
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.models import Payment, Quote
from porterchain_api.services.fleetbase_integration import get_fleetbase_integration
from porterchain_api.services.stripe_service import handle_checkout_completed
from porterchain_shared.events.catalog import DomainEventType

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
_confirmation = BookingConfirmationService()
_bookings = BookingService()
_payments = PaymentService()


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

    emit_event(
        db,
        event_type=DomainEventType.WEBHOOK_RECEIVED,
        aggregate_type="webhook",
        aggregate_id=event.get("id", "stripe"),
        payload={"source": "stripe", "type": event.get("type"), "data": event.get("data")},
    )
    db.commit()

    event_type = event["type"]
    data_object = event["data"]["object"]

    if event_type == "checkout.session.completed":
        meta = handle_checkout_completed(settings, data_object)
        if meta and meta.get("quote_id"):
            quote = db.query(Quote).filter(Quote.id == meta["quote_id"]).first()
            if quote:
                payment = None
                if meta.get("payment_id"):
                    payment = db.query(Payment).filter(Payment.id == meta["payment_id"]).first()
                if payment:
                    _payments.mark_succeeded(
                        db,
                        payment,
                        stripe_payment_intent_id=meta.get("payment_intent"),
                        receipt_url=meta.get("receipt_url"),
                    )
                _confirmation.complete_payment_and_create_order(
                    db,
                    settings,
                    quote,
                    stripe_payment_intent_id=meta.get("payment_intent"),
                    receipt_url=meta.get("receipt_url"),
                )

    elif event_type == "checkout.session.expired":
        session = data_object
        meta = session.get("metadata") or {}
        quote_id = meta.get("quote_id")
        if quote_id:
            quote = db.query(Quote).filter(Quote.id == quote_id).first()
            if quote:
                payment = _payments.get_active_payment(db, quote_id)
                if payment:
                    _payments.mark_failed(db, payment, reason="checkout_session_expired")
                _bookings.record_abandoned_checkout(db, quote, reason="session_expired")

    elif event_type in ("payment_intent.payment_failed", "checkout.session.async_payment_failed"):
        meta = data_object.get("metadata") or {}
        quote_id = meta.get("quote_id")
        if quote_id:
            quote = db.query(Quote).filter(Quote.id == quote_id).first()
            if quote:
                payment = _payments.get_active_payment(db, quote_id)
                if payment:
                    reason = data_object.get("last_payment_error", {}).get("message", "payment_failed")
                    _payments.mark_failed(db, payment, reason=reason)
                _bookings.record_abandoned_checkout(db, quote, reason="payment_failed")

    return {"status": "ok"}


@router.post("/fleetbase")
async def fleetbase_webhook(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    """Receive Fleetbase order lifecycle webhooks — emit domain event for async processing."""
    if not settings.fleetbase_dispatch_bridge:
        return {"status": "ignored", "reason": "bridge_disabled"}

    payload = await request.body()
    try:
        body = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid_json") from exc

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="invalid_payload")

    signature = request.headers.get("X-Fleetbase-Signature") or request.headers.get("X-Signature")
    integration = get_fleetbase_integration(settings)
    update = integration.process_webhook(payload, body, signature=signature)
    if not update:
        return {"status": "ignored"}

    order_id = update.get("porterchain_order_id") or update.get("fleetbase_order_id") or "unknown"
    emit_event(
        db,
        event_type=DomainEventType.WEBHOOK_RECEIVED,
        aggregate_type="webhook",
        aggregate_id=str(order_id),
        payload={"source": "fleetbase", "update": update, "raw": body},
    )
    db.commit()

    return {"status": "accepted", "order_id": update.get("porterchain_order_id")}
