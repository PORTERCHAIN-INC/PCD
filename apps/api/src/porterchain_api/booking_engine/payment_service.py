"""Payment service — Stripe integration per PRD Phase B."""

from sqlalchemy.orm import Session

from porterchain_api.booking_engine import events as E
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.booking_draft_service import BookingDraftService
from porterchain_api.booking_models import Customer, Payment, Quote
from porterchain_api.config import Settings
from porterchain_api.domain.states import PaymentStatus, QuoteState
from porterchain_api.services.stripe_service import create_checkout_session


class PaymentService:
    def __init__(self) -> None:
        self._drafts = BookingDraftService()

    def start_payment(
        self,
        db: Session,
        settings: Settings,
        quote: Quote,
        customer: Customer,
        *,
        checkout_channel: str = "retail",
    ) -> tuple[str | None, Payment]:
        from porterchain_api.booking_engine.quote_service import (
            revalidate_quote_for_payment,
        )

        quote = revalidate_quote_for_payment(db, quote)

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
        # 100% promo (or other full waive) → $0. Stripe Checkout rejects unit_amount=0.
        if int(quote.amount_cents or 0) <= 0:
            from porterchain_api.booking_engine.confirmation_service import (
                BookingConfirmationService,
            )

            payment.status = PaymentStatus.PROCESSING.value
            quote.state = QuoteState.PAYMENT_PENDING.value
            emit_event(
                db,
                event_type=E.CHECKOUT_STARTED,
                aggregate_type="quote",
                aggregate_id=quote.id,
                correlation_id=quote.id,
                payload={"free_promo": True, "payment_id": payment.id, "amount_cents": 0},
            )
            self._drafts.on_payment_started(
                db,
                quote,
                stripe_session_id=None,
                settings=settings,
            )
            db.flush()
            BookingConfirmationService().complete_payment_and_create_order(
                db,
                settings,
                quote,
                payment_method="promo",
                transaction_id=f"promo_free_{payment.id}",
            )
            success_base = (
                settings.customer_checkout_success_url
                if checkout_channel == "customer"
                else settings.retail_checkout_success_url
            )
            checkout_url = f"{success_base}?quote_id={quote.id}&free=1"
            db.commit()
            db.refresh(payment)
            db.refresh(quote)
            return checkout_url, payment

        if settings.allow_stripe_mock:
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
            draft = self._drafts.get_by_quote_id(db, quote.id)
            checkout_url, session_id = create_checkout_session(
                settings,
                quote,
                customer,
                payment.id,
                booking_draft_id=draft.id if draft else None,
                checkout_channel=checkout_channel,
            )
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
        self._drafts.on_payment_started(
            db,
            quote,
            stripe_session_id=payment.stripe_checkout_session_id,
            settings=settings,
        )
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

        quote = db.query(Quote).filter(Quote.id == payment.quote_id).first()
        customer = (
            db.query(Customer).filter(Customer.id == payment.customer_id).first()
            if payment.customer_id
            else None
        )
        if customer is None and quote and quote.customer_id:
            customer = db.query(Customer).filter(Customer.id == quote.customer_id).first()
        cents = int(payment.amount_cents or (quote.amount_cents if quote else 0) or 0)
        currency = payment.currency or (quote.currency if quote else "cad")
        emit_event(
            db,
            event_type=E.PAYMENT_SUCCEEDED,
            aggregate_type="payment",
            aggregate_id=payment.id,
            correlation_id=payment.quote_id,
            payload={
                "stripe_payment_intent_id": stripe_payment_intent_id,
                "receipt_url": receipt_url,
                "customer_id": payment.customer_id or (quote.customer_id if quote else None),
                "email": customer.email if customer else None,
                "amount_cents": cents,
                "amount_display": f"${cents / 100:.2f} {(currency or 'cad').upper()}",
                "currency": currency,
                "order_id": payment.order_id,
                "order_number": None,
            },
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
        BookingDraftService().on_payment_failed(db, payment.quote_id, reason=reason)
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
        *,
        checkout_channel: str = "retail",
    ) -> tuple[str | None, Payment]:
        existing = self.get_active_payment(db, quote.id)
        if existing and existing.status == PaymentStatus.FAILED.value:
            existing.retry_count += 1
            db.commit()
        return self.start_payment(db, settings, quote, customer, checkout_channel=checkout_channel)

    def retry_payment_for_clerk(
        self,
        db: Session,
        settings: Settings,
        *,
        quote_id: str,
        clerk_user_id: str,
    ) -> tuple[str | None, Payment]:
        quote = db.query(Quote).filter(Quote.id == quote_id).first()
        if not quote:
            raise LookupError("quote_not_found")
        if quote.state not in (QuoteState.PAYMENT_PENDING.value, QuoteState.BOOKING_PENDING.value):
            raise ValueError("quote_not_payable")

        customer = db.query(Customer).filter(Customer.clerk_user_id == clerk_user_id).first()
        if not customer or customer.id != quote.customer_id:
            raise PermissionError("forbidden")
        return self.retry_payment(db, settings, quote, customer)
