"""Booking confirmation — order, booking, invoice creation per PRD."""

from sqlalchemy.orm import Session

from porterchain_api.booking_engine import events as E
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.numbers import (
    generate_booking_number,
    generate_customer_reference,
    generate_invoice_number,
    generate_order_number,
    generate_payment_reference,
    generate_receipt_number,
    generate_tracking_number,
)
from porterchain_api.booking_engine.payment_service import PaymentService
from porterchain_api.booking_engine.booking_draft_service import BookingDraftService
from porterchain_api.config import Settings
from porterchain_api.domain.states import BookingState, OrderState, QuoteState
from porterchain_api.models import Booking, Customer, Invoice, Order, Payment, Quote
from porterchain_api.booking_engine.order_transitions import transition_order_state, transition_to_dispatch_ready
from porterchain_api.booking_engine.order_metadata import resolve_order_type, retail_order_source


class BookingConfirmationService:
    """Completes payment → booking → order → invoice; downstream via domain events."""

    def __init__(self) -> None:
        self._payments = PaymentService()
        self._drafts = BookingDraftService()

    def complete_payment_and_create_order(
        self,
        db: Session,
        settings: Settings,
        quote: Quote,
        *,
        stripe_payment_intent_id: str | None = None,
        receipt_url: str | None = None,
        payment_method: str | None = None,
        transaction_id: str | None = None,
        tax_cents: int | None = None,
        fees_cents: int | None = None,
    ) -> Order:
        if quote.state != QuoteState.PAYMENT_PENDING.value:
            raise ValueError("quote_not_awaiting_payment")

        # Idempotency — a verified webhook may arrive more than once.
        existing = db.query(Order).filter(Order.quote_id == quote.id).first()
        if existing:
            booking = db.query(Booking).filter(Booking.quote_id == quote.id).first()
            if booking:
                self._drafts.on_payment_completed(
                    db, quote, order_id=existing.id, booking_id=booking.id
                )
                self._drafts.on_booking_confirmed(db, quote, booking, existing)
            return existing

        payment = self._payments.get_active_payment(db, quote.id)
        if payment:
            self._payments.mark_succeeded(
                db,
                payment,
                stripe_payment_intent_id=stripe_payment_intent_id,
                receipt_url=receipt_url,
            )
            payment.payment_reference = payment.payment_reference or generate_payment_reference()
            payment.payment_method = payment_method or payment.payment_method
            payment.transaction_id = transaction_id or stripe_payment_intent_id

        if not quote.customer_id:
            raise ValueError("quote_missing_customer")

        # Ensure the customer has a stable business reference.
        customer = db.query(Customer).filter(Customer.id == quote.customer_id).first()
        if customer and not customer.customer_reference:
            customer.customer_reference = generate_customer_reference()

        booking = Booking(
            booking_number=generate_booking_number(),
            state=BookingState.BOOKED.value,
            quote_id=quote.id,
            customer_id=quote.customer_id,
        )
        db.add(booking)
        db.flush()

        order = Order(
            order_number=generate_order_number(),
            tracking_number=generate_tracking_number(),
            state=OrderState.BOOKED.value,
            quote_id=quote.id,
            customer_id=quote.customer_id,
            order_source=retail_order_source(),
            order_type=resolve_order_type(
                schedule_mode=quote.schedule_mode or "now",
                is_rush=quote.schedule_mode == "now",
            ),
            payment_terms="IMMEDIATE",
            amount_cents=quote.amount_cents,
            currency=quote.currency,
            stripe_payment_intent_id=stripe_payment_intent_id,
            pickup=quote.pickup,
            dropoff=quote.dropoff,
            scheduled_at=quote.scheduled_at,
        )
        db.add(order)
        db.flush()

        booking.order_id = order.id
        if payment:
            payment.order_id = order.id

        invoice = Invoice(
            invoice_number=generate_invoice_number(),
            receipt_number=generate_receipt_number(),
            order_id=order.id,
            customer_id=quote.customer_id,
            amount_cents=order.amount_cents,
            tax_cents=tax_cents or 0,
            fees_cents=fees_cents or 0,
            currency=order.currency,
            stripe_receipt_url=receipt_url,
        )
        db.add(invoice)
        db.flush()

        emit_event(
            db,
            event_type=E.BOOKING_CREATED,
            aggregate_type="booking",
            aggregate_id=booking.id,
            correlation_id=quote.id,
            payload={"booking_number": booking.booking_number},
        )
        emit_event(
            db,
            event_type=E.ORDER_CREATED,
            aggregate_type="order",
            aggregate_id=order.id,
            correlation_id=quote.id,
            payload={"order_number": order.order_number, "tracking_number": order.tracking_number},
        )
        emit_event(
            db,
            event_type=E.ORDER_BOOKED,
            aggregate_type="order",
            aggregate_id=order.id,
            correlation_id=quote.id,
            payload={"tracking_number": order.tracking_number},
        )
        emit_event(
            db,
            event_type=E.INVOICE_CREATED,
            aggregate_type="invoice",
            aggregate_id=invoice.id,
            correlation_id=order.id,
            payload={"invoice_number": invoice.invoice_number},
        )
        emit_event(
            db,
            event_type=E.ORDER_INVOICED,
            aggregate_type="order",
            aggregate_id=order.id,
            correlation_id=order.id,
            payload={"invoice_number": invoice.invoice_number, "invoice_id": invoice.id},
        )
        emit_event(
            db,
            event_type=E.RECEIPT_GENERATED,
            aggregate_type="invoice",
            aggregate_id=invoice.id,
            correlation_id=order.id,
            payload={
                "receipt_number": invoice.receipt_number,
                "payment_reference": payment.payment_reference if payment else None,
                "receipt_url": receipt_url,
            },
        )
        db.commit()

        transition_to_dispatch_ready(
            db,
            order,
            event_type=E.ORDER_DISPATCH_READY,
            payload={},
        )

        emit_event(
            db,
            event_type=E.BOOKING_CONFIRMED,
            aggregate_type="booking",
            aggregate_id=booking.id,
            correlation_id=order.id,
            payload={
                "order_id": order.id,
                "email": customer.email if customer else None,
                "phone": customer.phone if customer else None,
                "tracking_number": order.tracking_number,
                "order_number": order.order_number,
                "invoice_number": invoice.invoice_number,
                "receipt_number": invoice.receipt_number,
                "booking_number": booking.booking_number,
                "payment_reference": payment.payment_reference if payment else None,
                "customer_reference": customer.customer_reference if customer else None,
                "amount_cents": order.amount_cents,
                "currency": order.currency,
            },
        )
        self._drafts.on_payment_completed(
            db,
            quote,
            order_id=order.id,
            booking_id=booking.id,
        )
        self._drafts.on_booking_confirmed(db, quote, booking, order)
        db.commit()

        db.refresh(order)
        return order

    def get_confirmation_status(self, db: Session, quote_id: str) -> tuple[str, Order | None]:
        order = db.query(Order).filter(Order.quote_id == quote_id).first()
        if not order:
            return "processing", None
        return "ready", order

    def build_confirmation_response(self, db: Session, order: Order) -> dict:
        booking = db.query(Booking).filter(Booking.order_id == order.id).first()
        invoice = db.query(Invoice).filter(Invoice.order_id == order.id).first()
        payment = (
            db.query(Payment)
            .filter(Payment.order_id == order.id)
            .order_by(Payment.created_at.desc())
            .first()
        )
        customer = db.query(Customer).filter(Customer.id == order.customer_id).first() if order.customer_id else None
        return {
            "booking_id": booking.id if booking else "",
            "booking_number": booking.booking_number if booking else "",
            "order_id": order.id,
            "order_number": order.order_number,
            "tracking_number": order.tracking_number,
            "invoice_id": invoice.id if invoice else "",
            "invoice_number": invoice.invoice_number if invoice else "",
            "receipt_number": invoice.receipt_number if invoice else None,
            "payment_reference": payment.payment_reference if payment else None,
            "customer_reference": customer.customer_reference if customer else None,
            "payment_method": payment.payment_method if payment else None,
            "receipt_url": invoice.stripe_receipt_url if invoice else None,
            "tax_cents": invoice.tax_cents if invoice else 0,
            "state": order.state,
            "amount_cents": order.amount_cents,
            "currency": order.currency,
            "scheduled_at": order.scheduled_at,
            "pickup": order.pickup,
            "dropoff": order.dropoff,
            "fleetbase_order_id": order.fleetbase_order_id,
        }

    def mock_complete_checkout(self, db: Session, settings: Settings, quote_id: str) -> Order:
        quote = db.query(Quote).filter(Quote.id == quote_id).first()
        if not quote:
            raise LookupError("quote_not_found")
        if quote.state != QuoteState.PAYMENT_PENDING.value:
            raise ValueError("quote_not_awaiting_payment")
        return self.complete_payment_and_create_order(
            db, settings, quote, stripe_payment_intent_id="mock_pi"
        )
