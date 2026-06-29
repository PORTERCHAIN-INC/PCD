"""Booking confirmation — order, booking, invoice creation per PRD."""

from sqlalchemy.orm import Session

from porterchain_api.booking_engine import events as E
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.numbers import (
    generate_booking_number,
    generate_invoice_number,
    generate_order_number,
    generate_tracking_number,
)
from porterchain_api.booking_engine.payment_service import PaymentService
from porterchain_api.config import Settings
from porterchain_api.domain.states import BookingState, OrderState, QuoteState
from porterchain_api.models import Booking, Customer, Invoice, Order, Payment, Quote
from porterchain_api.booking_engine.order_transitions import transition_order_state


class BookingConfirmationService:
    """Completes payment → booking → order → invoice; downstream via domain events."""

    def __init__(self) -> None:
        self._payments = PaymentService()

    def complete_payment_and_create_order(
        self,
        db: Session,
        settings: Settings,
        quote: Quote,
        *,
        stripe_payment_intent_id: str | None = None,
        receipt_url: str | None = None,
    ) -> Order:
        if quote.state != QuoteState.PAYMENT_PENDING.value:
            raise ValueError("quote_not_awaiting_payment")

        existing = db.query(Order).filter(Order.quote_id == quote.id).first()
        if existing:
            return existing

        payment = self._payments.get_active_payment(db, quote.id)
        if payment:
            self._payments.mark_succeeded(
                db,
                payment,
                stripe_payment_intent_id=stripe_payment_intent_id,
                receipt_url=receipt_url,
            )

        if not quote.customer_id:
            raise ValueError("quote_missing_customer")

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
            order_id=order.id,
            customer_id=quote.customer_id,
            amount_cents=order.amount_cents,
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
        db.commit()

        transition_order_state(
            db,
            order,
            OrderState.DISPATCH_READY,
            event_type=E.ORDER_DISPATCH_READY,
            payload={},
        )

        customer = db.query(Customer).filter(Customer.id == quote.customer_id).first()
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
                "booking_number": booking.booking_number,
            },
        )
        db.commit()

        db.refresh(order)
        return order
