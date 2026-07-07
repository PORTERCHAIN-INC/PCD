"""Tracking service — customer-facing shipment status."""

from sqlalchemy.orm import Session

from porterchain_api.fleetbase_engine.integration_bridge import FleetbaseIntegrationBridge
from porterchain_api.config import Settings
from porterchain_api.models import Booking, Invoice, Order, Payment


class TrackingService:
    def __init__(self) -> None:
        self._fleetbase = FleetbaseIntegrationBridge()

    def get_by_tracking(self, db: Session, tracking_number: str) -> Order | None:
        return db.query(Order).filter(Order.tracking_number == tracking_number).first()

    def get_live_tracking(
        self,
        db: Session,
        settings: Settings,
        order: Order,
    ) -> dict | None:
        """Pull live GPS/status from Fleetbase logistics engine."""
        return self._fleetbase.fetch_tracking(settings, order)

    def get_customer_dashboard(self, db: Session, customer_id: str) -> dict:
        orders = (
            db.query(Order)
            .filter(Order.customer_id == customer_id)
            .order_by(Order.created_at.desc())
            .limit(50)
            .all()
        )
        bookings = (
            db.query(Booking)
            .filter(Booking.customer_id == customer_id)
            .order_by(Booking.created_at.desc())
            .limit(50)
            .all()
        )
        invoices = (
            db.query(Invoice)
            .filter(Invoice.customer_id == customer_id)
            .order_by(Invoice.created_at.desc())
            .limit(50)
            .all()
        )
        payments = (
            db.query(Payment)
            .filter(Payment.customer_id == customer_id)
            .order_by(Payment.created_at.desc())
            .limit(20)
            .all()
        )
        active = next((o for o in orders if o.state not in ("CLOSED", "CANCELLED", "REFUNDED")), None)
        return {
            "active_order": self._serialize_order(active) if active else None,
            "orders": [self._serialize_order(o) for o in orders],
            "bookings": [self._serialize_booking(b) for b in bookings],
            "invoices": [self._serialize_invoice(i) for i in invoices],
            "payments": [self._serialize_payment(p) for p in payments],
            "stats": {
                "total_orders": len(orders),
                "total_bookings": len(bookings),
            },
        }

    def _serialize_order(self, order: Order) -> dict:
        return {
            "order_id": order.id,
            "order_number": order.order_number,
            "tracking_number": order.tracking_number,
            "state": order.state,
            "amount_cents": order.amount_cents,
            "currency": order.currency,
            "scheduled_at": order.scheduled_at.isoformat(),
            "pickup": order.pickup,
            "dropoff": order.dropoff,
            "fleetbase_order_id": order.fleetbase_order_id,
            "created_at": order.created_at.isoformat(),
        }

    def _serialize_booking(self, booking: Booking) -> dict:
        return {
            "booking_id": booking.id,
            "booking_number": booking.booking_number,
            "state": booking.state,
            "quote_id": booking.quote_id,
            "order_id": booking.order_id,
            "created_at": booking.created_at.isoformat(),
        }

    def _serialize_invoice(self, invoice: Invoice) -> dict:
        return {
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "order_id": invoice.order_id,
            "amount_cents": invoice.amount_cents,
            "currency": invoice.currency,
            "stripe_receipt_url": invoice.stripe_receipt_url,
            "pdf_url": invoice.pdf_url,
            "created_at": invoice.created_at.isoformat(),
        }

    def _serialize_payment(self, payment: Payment) -> dict:
        return {
            "payment_id": payment.id,
            "status": payment.status,
            "amount_cents": payment.amount_cents,
            "currency": payment.currency,
            "failure_reason": payment.failure_reason,
            "receipt_url": payment.receipt_url,
            "retry_count": payment.retry_count,
            "quote_id": payment.quote_id,
            "order_id": payment.order_id,
        }
