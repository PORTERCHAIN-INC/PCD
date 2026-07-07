"""Stripe webhook processing — idempotent by Stripe event ID."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_engine import BookingConfirmationService, BookingService, PaymentService
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.row_locks import lock_active_payment, lock_payment, lock_quote
from porterchain_api.config import Settings
from porterchain_api.models import Order, Payment, Quote
from porterchain_api.services.stripe_service import handle_checkout_completed
from porterchain_event_bus import get_event_bus
from porterchain_shared.events.catalog import DomainEventType

logger = logging.getLogger(__name__)


class StripeWebhookService:
    def __init__(self) -> None:
        self._confirmation = BookingConfirmationService()
        self._bookings = BookingService()
        self._payments = PaymentService()

    def handle(self, db: Session, settings: Settings, event: dict[str, Any]) -> dict[str, str]:
        stripe_event_id = event.get("id")
        if not stripe_event_id:
            raise ValueError("stripe_event_missing_id")

        idempotency_key = f"stripe:{stripe_event_id}"
        store = get_event_bus().idempotency
        if store.is_processed(idempotency_key):
            logger.info("skipping duplicate Stripe webhook %s", stripe_event_id)
            return {"status": "duplicate"}

        emit_event(
            db,
            event_type=DomainEventType.WEBHOOK_RECEIVED,
            aggregate_type="webhook",
            aggregate_id=stripe_event_id,
            payload={"source": "stripe", "type": event.get("type"), "data": event.get("data")},
        )
        db.commit()

        event_type = event["type"]
        data_object = event["data"]["object"]

        if event_type == "checkout.session.completed":
            self._handle_checkout_completed(db, settings, data_object)
        elif event_type == "checkout.session.expired":
            self._handle_checkout_expired(db, data_object)
        elif event_type in ("payment_intent.payment_failed", "checkout.session.async_payment_failed"):
            self._handle_payment_failed(db, data_object)

        store.mark_processed(idempotency_key)
        return {"status": "ok"}

    def _handle_checkout_completed(self, db: Session, settings: Settings, session: dict[str, Any]) -> None:
        meta = handle_checkout_completed(settings, session)
        if not meta or not meta.get("quote_id"):
            return
        quote = lock_quote(db, meta["quote_id"])
        if not quote:
            return
        payment = None
        if meta.get("payment_id"):
            payment = lock_payment(db, meta["payment_id"])
        if payment:
            self._payments.mark_succeeded(
                db,
                payment,
                stripe_payment_intent_id=meta.get("payment_intent"),
                receipt_url=meta.get("receipt_url"),
            )
        self._confirmation.complete_payment_and_create_order(
            db,
            settings,
            quote,
            stripe_payment_intent_id=meta.get("payment_intent"),
            receipt_url=meta.get("receipt_url"),
            payment_method=meta.get("payment_method"),
            transaction_id=meta.get("transaction_id"),
            tax_cents=meta.get("tax_cents"),
        )

    def _handle_checkout_expired(self, db: Session, session: dict[str, Any]) -> None:
        meta = session.get("metadata") or {}
        quote_id = meta.get("quote_id")
        if not quote_id:
            return
        quote = lock_quote(db, quote_id)
        if not quote:
            return
        payment = lock_active_payment(db, quote_id)
        if payment:
            self._payments.mark_failed(db, payment, reason="checkout_session_expired")
        self._bookings.record_abandoned_checkout(db, quote, reason="session_expired")

    def _handle_payment_failed(self, db: Session, data_object: dict[str, Any]) -> None:
        meta = data_object.get("metadata") or {}
        quote_id = meta.get("quote_id")
        if not quote_id:
            return
        quote = lock_quote(db, quote_id)
        if not quote:
            return
        payment = lock_active_payment(db, quote_id)
        if payment:
            reason = data_object.get("last_payment_error", {}).get("message", "payment_failed")
            self._payments.mark_failed(db, payment, reason=reason)
        self._bookings.record_abandoned_checkout(db, quote, reason="payment_failed")

    def sync_checkout_session(self, db: Session, settings: Settings, quote_id: str) -> bool:
        """Confirm a paid Stripe Checkout session when the webhook has not arrived yet."""
        if not settings.stripe_secret:
            return False

        quote = db.query(Quote).filter(Quote.id == quote_id).first()
        if not quote:
            return False
        if db.query(Order).filter(Order.quote_id == quote_id).first():
            return True

        payment = self._payments.get_active_payment(db, quote_id)
        session_id = (
            payment.stripe_checkout_session_id
            if payment and payment.stripe_checkout_session_id
            else quote.stripe_checkout_session_id
        )
        if not session_id:
            return False

        import stripe

        stripe.api_key = settings.stripe_secret
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status != "paid" and session.status != "complete":
            return False

        session_payload = session.to_dict()
        self._handle_checkout_completed(db, settings, session_payload)
        return True
