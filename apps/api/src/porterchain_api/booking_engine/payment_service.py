"""Payment service — Stripe integration per PRD Phase B."""

from sqlalchemy.orm import Session

from porterchain_api.booking_engine import events as E
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.config import Settings
from porterchain_api.domain.states import PaymentStatus, QuoteState
from porterchain_api.models import Customer, Payment, Quote
from porterchain_api.services.stripe_service import create_checkout_session


class PaymentService:
    def start_payment(
        self,
        db: Session,
        settings: Settings,
        quote: Quote,
        customer: Customer,
    ) -> tuple[str | None, Payment]:
        payment = Payment(
            quote_id=quote.id,
            customer_id=customer.id,
            status=PaymentStatus.PENDING.value,
            amount_cents=quote.amount_cents,
            currency=quote.currency,
        )
        db.add(payment)
        db.flush()

        emit_event(
            db,
            event_type=E.PAYMENT_STARTED,
            aggregate_type="payment",
            aggregate_id=payment.id,
            correlation_id=quote.id,
            actor_type="customer",
            actor_id=customer.id,
        )

        checkout_url: str | None = None
        if settings.stripe_mock or not settings.stripe_secret:
            payment.status = PaymentStatus.PROCESSING.value
            emit_event(
                db,
                event_type=E.CHECKOUT_STARTED,
                aggregate_type="quote",
                aggregate_id=quote.id,
                correlation_id=quote.id,
                payload={"mock": True, "payment_id": payment.id},
            )
        else:
            checkout_url, session_id = create_checkout_session(settings, quote, customer, payment.id)
            payment.stripe_checkout_session_id = session_id
            payment.status = PaymentStatus.PROCESSING.value
            quote.stripe_checkout_session_id = session_id
            emit_event(
                db,
                event_type=E.CHECKOUT_STARTED,
                aggregate_type="quote",
                aggregate_id=quote.id,
                correlation_id=quote.id,
                payload={"stripe_session_id": session_id, "payment_id": payment.id},
            )

        quote.state = QuoteState.PAYMENT_PENDING.value
        db.commit()
        db.refresh(payment)
        db.refresh(quote)
        return checkout_url, payment

    def mark_succeeded(
        self,
        db: Session,
        payment: Payment,
        *,
        stripe_payment_intent_id: str | None = None,
        receipt_url: str | None = None,
    ) -> Payment:
        payment.status = PaymentStatus.SUCCEEDED.value
        payment.stripe_payment_intent_id = stripe_payment_intent_id
        payment.receipt_url = receipt_url
        emit_event(
            db,
            event_type=E.PAYMENT_SUCCEEDED,
            aggregate_type="payment",
            aggregate_id=payment.id,
            correlation_id=payment.quote_id,
            payload={"stripe_payment_intent_id": stripe_payment_intent_id},
        )
        db.commit()
        db.refresh(payment)
        return payment

    def mark_failed(
        self,
        db: Session,
        payment: Payment,
        *,
        reason: str,
    ) -> Payment:
        payment.status = PaymentStatus.FAILED.value
        payment.failure_reason = reason
        emit_event(
            db,
            event_type=E.PAYMENT_FAILED,
            aggregate_type="payment",
            aggregate_id=payment.id,
            correlation_id=payment.quote_id,
            payload={"reason": reason},
        )
        db.commit()
        db.refresh(payment)
        return payment

    def get_active_payment(self, db: Session, quote_id: str) -> Payment | None:
        return (
            db.query(Payment)
            .filter(Payment.quote_id == quote_id)
            .order_by(Payment.created_at.desc())
            .first()
        )

    def retry_payment(
        self,
        db: Session,
        settings: Settings,
        quote: Quote,
        customer: Customer,
    ) -> tuple[str | None, Payment]:
        existing = self.get_active_payment(db, quote.id)
        if existing and existing.status == PaymentStatus.FAILED.value:
            existing.retry_count += 1
            db.commit()
        return self.start_payment(db, settings, quote, customer)
