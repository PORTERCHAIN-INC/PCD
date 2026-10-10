"""Booking confirmation — order, booking, invoice creation per PRD."""

from sqlalchemy.orm import Session

from porterchain_api.booking_engine import events as E
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.booking_draft_service import BookingDraftService
from porterchain_api.booking_engine.numbers import (
    generate_booking_number,
    generate_customer_reference,
    generate_invoice_number,
    generate_order_number,
    generate_payment_reference,
    generate_receipt_number,
    generate_tracking_number,
)
from porterchain_api.booking_engine.order_metadata import (
    resolve_order_type,
    retail_order_source,
)
from porterchain_api.booking_engine.order_transitions import (
    transition_to_dispatch_ready,
)
from porterchain_api.booking_engine.payment_service import PaymentService
from porterchain_api.booking_engine.row_locks import (
    lock_active_payment,
    lock_order_by_quote,
    lock_quote,
)
from porterchain_api.booking_models import (
    Booking,
    Customer,
    Invoice,
    Order,
    Payment,
    Quote,
)
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderState, QuoteState


def _retail_compliance_from_quote(quote: Quote) -> dict | None:
    """Persist quote stops and parcels onto the order. Extra stops are drops, not parcel splits."""
    from porterchain_api.domain.customer_goods import persist_vehicle_class

    extras = quote.additional_stops if isinstance(quote.additional_stops, list) else []
    payload = quote.parcels if isinstance(quote.parcels, dict) else {}
    if not extras and not payload:
        if not quote.vehicle_class:
            return None
        return {"vehicle_class": persist_vehicle_class(quote.vehicle_class)}
    pickup = quote.pickup if isinstance(quote.pickup, dict) else {}
    dropoff = quote.dropoff if isinstance(quote.dropoff, dict) else {}
    stops: list[dict] = []
    seq = 0
    if pickup:
        stops.append(
            {
                "id": "s0",
                "type": "pickup",
                "sequence": seq,
                "formatted": pickup.get("formatted") or pickup.get("address"),
                "address": pickup.get("formatted") or pickup.get("address"),
                "lat": pickup.get("lat"),
                "lng": pickup.get("lng"),
                "city": pickup.get("city"),
            }
        )
        seq += 1
    for i, raw in enumerate(extras):
        s = raw if isinstance(raw, dict) else {}
        stops.append(
            {
                "id": f"s{seq}",
                "type": "dropoff",
                "sequence": seq,
                "formatted": s.get("formatted") or s.get("address"),
                "address": s.get("formatted") or s.get("address"),
                "lat": s.get("lat"),
                "lng": s.get("lng"),
                "city": s.get("city"),
            }
        )
        seq += 1
        del i
    if dropoff:
        stops.append(
            {
                "id": f"s{seq}",
                "type": "dropoff",
                "sequence": seq,
                "formatted": dropoff.get("formatted") or dropoff.get("address"),
                "address": dropoff.get("formatted") or dropoff.get("address"),
                "lat": dropoff.get("lat"),
                "lng": dropoff.get("lng"),
                "city": dropoff.get("city"),
            }
        )
    items = [] if payload.get("booking_mode") == "vehicle" else list(payload.get("items") or [])
    if items:
        for stop in reversed(stops):
            if stop.get("type") == "dropoff":
                stop["packages"] = items
                break
    return {
        "stops": stops,
        "order_kind": "hub_spoke" if len(extras) >= 1 else "single",
        "additional_stops": extras,
        "vehicle_class": persist_vehicle_class(quote.vehicle_class),
        "schedule_mode": quote.schedule_mode,
        "booking_mode": payload.get("booking_mode") or "parcels",
        "parcels": payload,
        "weight_kg": None if payload.get("booking_mode") == "vehicle" else quote.weight_kg,
    }


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
        locked_quote = lock_quote(db, quote.id)
        if not locked_quote:
            raise LookupError("quote_not_found")
        quote = locked_quote

        if quote.state != QuoteState.PAYMENT_PENDING.value:
            raise ValueError("quote_not_awaiting_payment")

        # Idempotency — a verified webhook may arrive more than once.
        existing = lock_order_by_quote(db, quote.id)
        if existing:
            booking = db.query(Booking).filter(Booking.quote_id == quote.id).first()
            if booking:
                self._drafts.on_payment_completed(
                    db, quote, order_id=existing.id, booking_id=booking.id
                )
                self._drafts.on_booking_confirmed(db, quote, booking, existing)
            return existing

        payment = lock_active_payment(db, quote.id)
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

        # Ensure the customer has a stable business reference (C-25: retry on collision).
        customer = db.query(Customer).filter(Customer.id == quote.customer_id).first()
        if customer and not customer.customer_reference:
            self._assign_customer_reference(db, customer)

        booking = Booking(
            booking_number=generate_booking_number(),
            state=OrderState.BOOKED.value,
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
            compliance_metadata=_retail_compliance_from_quote(quote),
        )
        db.add(order)
        db.flush()

        booking.order_id = order.id
        if payment:
            payment.order_id = order.id

        from porterchain_api.admin_engine.platform_settings import (
            invoice_number_prefix,
            receipt_number_prefix,
            tax_cents_for_amount,
        )

        resolved_tax = (
            tax_cents if tax_cents is not None else tax_cents_for_amount(db, int(order.amount_cents or 0))
        )
        invoice = Invoice(
            invoice_number=generate_invoice_number(prefix=invoice_number_prefix(db)),
            receipt_number=generate_receipt_number(prefix=receipt_number_prefix(db)),
            order_id=order.id,
            customer_id=quote.customer_id,
            amount_cents=order.amount_cents,
            tax_cents=int(resolved_tax or 0),
            fees_cents=fees_cents or 0,
            currency=order.currency,
            stripe_receipt_url=receipt_url,
        )
        db.add(invoice)
        db.flush()
        from porterchain_api.billing_engine.invoice_document import (
            attach_invoice_document,
        )
        from porterchain_api.booking_engine.stop_sync import dual_write_stops

        dual_write_stops(db, order)
        attach_invoice_document(db, invoice, order, payment)

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
            payload={
                "order_number": order.order_number,
                "tracking_number": order.tracking_number,
                "customer_id": quote.customer_id,
                "merchant_id": order.merchant_id,
                "email": customer.email if customer else None,
            },
        )
        emit_event(
            db,
            event_type=E.ORDER_BOOKED,
            aggregate_type="order",
            aggregate_id=order.id,
            correlation_id=quote.id,
            payload={
                "tracking_number": order.tracking_number,
                "order_number": order.order_number,
                "customer_id": quote.customer_id,
                "merchant_id": order.merchant_id,
                "email": customer.email if customer else None,
            },
        )
        amount_display = f"${(order.amount_cents or 0) / 100:.2f} {(order.currency or 'cad').upper()}"
        receipt_payload = {
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "receipt_number": invoice.receipt_number,
            "payment_reference": payment.payment_reference if payment else None,
            "receipt_url": receipt_url,
            "customer_id": quote.customer_id,
            "email": customer.email if customer else None,
            "order_id": order.id,
            "order_number": order.order_number,
            "tracking_number": order.tracking_number,
            "amount_cents": order.amount_cents,
            "amount_display": amount_display,
            "currency": order.currency,
            "customer_deep_link": (
                f"{settings.customer_portal_url.rstrip('/')}/invoices/{invoice.id}"
            ),
            "merchant_deep_link": (
                f"{settings.merchant_portal_url.rstrip('/')}/billing/invoices/{invoice.id}"
            ),
            "merchant_id": order.merchant_id,
        }
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
            payload=receipt_payload,
        )
        emit_event(
            db,
            event_type=E.RECEIPT_GENERATED,
            aggregate_type="invoice",
            aggregate_id=invoice.id,
            correlation_id=order.id,
            payload=receipt_payload,
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
                "customer_id": quote.customer_id,
                "email": customer.email if customer else None,
                "phone": customer.phone if customer else None,
                "tracking_number": order.tracking_number,
                "order_number": order.order_number,
                "invoice_number": invoice.invoice_number,
                "receipt_number": invoice.receipt_number,
                "receipt_url": receipt_url,
                "booking_number": booking.booking_number,
                "payment_reference": payment.payment_reference if payment else None,
                "customer_reference": customer.customer_reference if customer else None,
                "amount_cents": order.amount_cents,
                "amount_display": amount_display,
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
            "vehicle_class": (order.compliance_metadata or {}).get("vehicle_class")
            if isinstance(order.compliance_metadata, dict)
            else None,
            "booking_mode": (order.compliance_metadata or {}).get("booking_mode")
            if isinstance(order.compliance_metadata, dict)
            else None,
            "parcels": ((order.compliance_metadata or {}).get("parcels") or {}).get("items")
            if isinstance(order.compliance_metadata, dict)
            and isinstance((order.compliance_metadata or {}).get("parcels"), dict)
            else None,
        }

    @staticmethod
    def _assign_customer_reference(db: Session, customer: Customer, *, attempts: int = 8) -> None:
        """C-25: unique customer_reference — probe + nested savepoint on collision."""
        from sqlalchemy.exc import IntegrityError

        for _ in range(attempts):
            ref = generate_customer_reference()
            taken = (
                db.query(Customer.id)
                .filter(Customer.customer_reference == ref, Customer.id != customer.id)
                .first()
            )
            if taken:
                continue
            customer.customer_reference = ref
            try:
                with db.begin_nested():
                    db.flush()
                return
            except IntegrityError:
                customer.customer_reference = None
                continue
        raise ValueError("customer_reference_collision")

    def mock_complete_checkout(self, db: Session, settings: Settings, quote_id: str) -> Order:
        quote = lock_quote(db, quote_id)
        if not quote:
            raise LookupError("quote_not_found")
        if quote.state != QuoteState.PAYMENT_PENDING.value:
            raise ValueError("quote_not_awaiting_payment")
        return self.complete_payment_and_create_order(
            db, settings, quote, stripe_payment_intent_id="mock_pi"
        )
