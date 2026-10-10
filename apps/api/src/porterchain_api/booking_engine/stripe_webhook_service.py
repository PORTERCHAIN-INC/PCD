"""Stripe webhook processing — idempotent by Stripe event ID."""

from __future__ import annotations

import logging
from typing import Any

from porterchain_event_bus import get_event_bus
from porterchain_shared.events.catalog import DomainEventType
from sqlalchemy.orm import Session

from porterchain_api.booking_engine import (
    BookingConfirmationService,
    BookingService,
    PaymentService,
)
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.row_locks import (
    lock_active_payment,
    lock_payment,
    lock_quote,
)
from porterchain_api.booking_engine.stripe_webhook_idempotency import (
    claim_stripe_event,
    complete_stripe_event,
    release_stripe_event,
)
from porterchain_api.platform.stripe_money import HANDLED_EVENTS as STRIPE_MONEY_EVENTS
from porterchain_api.platform.stripe_money import handle_stripe_money_event
from porterchain_api.booking_models import Invoice, Order, Payment, Quote
from porterchain_api.config import Settings
from porterchain_api.services.stripe_service import handle_checkout_completed

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

        event_type = event.get("type") or "unknown"
        if not claim_stripe_event(db, stripe_event_id=stripe_event_id, event_type=event_type):
            logger.info("skipping duplicate Stripe webhook %s (postgres)", stripe_event_id)
            return {"status": "duplicate"}

        try:
            emit_event(
                db,
                event_type=DomainEventType.WEBHOOK_RECEIVED,
                aggregate_type="webhook",
                aggregate_id=stripe_event_id,
                payload={"source": "stripe", "type": event.get("type"), "data": event.get("data")},
            )
            db.commit()

            data_object = event["data"]["object"]

            if event_type == "checkout.session.completed":
                session_obj = data_object
                meta = session_obj.get("metadata") or {}
                if meta.get("purpose") == "cod":
                    self._handle_cod_checkout_completed(db, settings, session_obj)
                else:
                    self._handle_checkout_completed(db, settings, session_obj)
            elif event_type == "checkout.session.expired":
                self._handle_checkout_expired(db, data_object)
            elif event_type in ("payment_intent.payment_failed", "checkout.session.async_payment_failed"):
                self._handle_payment_failed(db, data_object)
            elif event_type in STRIPE_MONEY_EVENTS:
                # Dashboard refunds, disputes, payouts (fees reconciled on payout.paid).
                handle_stripe_money_event(db, settings, event_type, data_object)
            elif event_type in (
                "identity.verification_session.verified",
                "identity.verification_session.requires_input",
                "identity.verification_session.canceled",
            ):
                self._handle_identity_verification_session(db, data_object)

            complete_stripe_event(db, stripe_event_id=stripe_event_id)
            db.commit()
            store.mark_processed(idempotency_key)
            return {"status": "ok"}
        except Exception:
            # Flush/commit failures leave the session needing rollback before
            # any further ORM work (e.g. releasing the claim row).
            db.rollback()
            try:
                release_stripe_event(db, stripe_event_id=stripe_event_id)
                db.commit()
            except Exception:
                db.rollback()
                logger.exception(
                    "failed to release stripe webhook claim after error event_id=%s",
                    stripe_event_id,
                )
            raise

    def _handle_identity_verification_session(self, db: Session, session_obj: dict[str, Any]) -> None:
        from porterchain_api.driver_engine.verification_service import (
            DriverVerificationService,
        )

        DriverVerificationService().apply_stripe_identity_event(db, session_obj)

    def _handle_cod_checkout_completed(
        self, db: Session, settings: Settings, session: dict[str, Any]
    ) -> None:
        from porterchain_api.billing_engine.stripe_cod_service import StripeCodService
        from porterchain_api.merchant_engine import shopify_service as shopify_svc

        meta = session.get("metadata") or {}
        order_id = meta.get("order_id")
        if not order_id:
            logger.warning("cod_checkout_missing_order_id session=%s", session.get("id"))
            return
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            logger.warning("cod_checkout_order_not_found order_id=%s", order_id)
            return
        if (order.cod_status or "").lower() in ("collected", "payout_processed"):
            return
        pi = session.get("payment_intent")
        if isinstance(pi, dict):
            pi = pi.get("id")
        StripeCodService().mark_cod_collected(
            db,
            order,
            payment_intent_id=str(pi) if pi else None,
            session_id=session.get("id"),
        )
        try:
            shopify_svc.capture_cod_transaction(db, settings, order)
        except Exception:
            logger.exception("shopify_cod_capture_failed order=%s", order.id)

    def _handle_checkout_completed(self, db: Session, settings: Settings, session: dict[str, Any]) -> None:
        meta = handle_checkout_completed(settings, session)
        if not meta:
            return
        if meta.get("kind") == "additional_stop":
            from porterchain_driver.field_admin import merge_additional_payment

            if meta.get("payment_id"):
                merge_additional_payment(db, meta["payment_id"])
            return
        if meta.get("invoice_id"):
            self._handle_invoice_checkout_completed(db, session, meta)
            return
        if not meta.get("quote_id"):
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

    def _handle_invoice_checkout_completed(
        self, db: Session, session: dict[str, Any], meta: dict[str, Any]
    ) -> None:
        from porterchain_api.billing_engine.models import BillingLedgerEntry
        from porterchain_api.merchant_engine.billing_service import (
            MerchantBillingService,
        )

        payment = None
        if meta.get("payment_id"):
            payment = lock_payment(db, meta["payment_id"])
        invoice_id = meta.get("invoice_id")

        # Pay-all batch: payment_id → ledger metadata.invoice_ids
        if payment and (invoice_id in (None, "", "batch") or payment.payment_reference == "pay_all"):
            batch = (
                db.query(BillingLedgerEntry)
                .filter(
                    BillingLedgerEntry.payment_id == payment.id,
                    BillingLedgerEntry.kind == "merchant_invoice_pay_batch",
                )
                .first()
            )
            ids = list((batch.metadata_json or {}).get("invoice_ids") or []) if batch else []
            merchant_id = meta.get("merchant_id") or (batch.merchant_id if batch else None)
            if ids and merchant_id:
                MerchantBillingService()._settle_invoice_batch(
                    db,
                    merchant_id,
                    [str(i) for i in ids],
                    payment=payment,
                    stripe_payment_intent_id=meta.get("payment_intent"),
                    receipt_url=meta.get("receipt_url"),
                    session_id=session.get("id"),
                )
                db.commit()
            return

        if not invoice_id:
            return
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return
        if payment is None:
            payment = (
                db.query(Payment)
                .filter(Payment.invoice_id == invoice_id, Payment.status == "PENDING")
                .order_by(Payment.created_at.desc())
                .first()
            )
        if payment is None:
            return
        if meta.get("merchant_id") and invoice.merchant_id and meta["merchant_id"] != invoice.merchant_id:
            logger.warning(
                "invoice_checkout_merchant_mismatch invoice=%s meta=%s",
                invoice_id,
                meta.get("merchant_id"),
            )
            return
        order = db.query(Order).filter(Order.id == invoice.order_id).first() if invoice.order_id else None
        MerchantBillingService()._settle_invoice_payment(
            db,
            invoice=invoice,
            order=order,
            payment=payment,
            stripe_payment_intent_id=meta.get("payment_intent"),
            receipt_url=meta.get("receipt_url"),
            session_id=session.get("id"),
        )
        db.commit()

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

        from porterchain_api.services.stripe_service import retrieve_checkout_session

        session_payload = retrieve_checkout_session(settings, session_id)
        if session_payload.get("payment_status") != "paid" and session_payload.get("status") != "complete":
            return False

        self._handle_checkout_completed(db, settings, session_payload)
        return True
