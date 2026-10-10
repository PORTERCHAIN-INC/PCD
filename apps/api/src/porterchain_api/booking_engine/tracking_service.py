"""Tracking service — customer-facing shipment status."""

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_engine.public_address import public_address_snapshot
from porterchain_api.booking_engine.public_tracking_snapshot import (
    build_public_live_tracking,
)
from porterchain_api.booking_engine.repositories.order_repository import OrderRepository
from porterchain_api.booking_engine.tracking_normalize import TrackingFacade
from porterchain_api.booking_models import Booking, Customer, Invoice, Order, Payment
from porterchain_api.config import Settings
from porterchain_api.merchant_engine.organization_sync import public_shipper_branding
from porterchain_api.merchant_models import Merchant
from porterchain_api.schemas import OrderResponse, OrderTrackingResponse


class TrackingService:
    def __init__(self) -> None:
        self._facade = TrackingFacade()
        self._orders = OrderRepository()

    def get_by_tracking(self, db: Session, tracking_number: str) -> Order | None:
        return db.query(Order).filter(Order.tracking_number == tracking_number).first()

    def _order_response_from_order(
        self,
        db: Session,
        order: Order,
        *,
        public: bool = False,
    ) -> OrderResponse:
        booking = db.query(Booking).filter(Booking.order_id == order.id).first()
        invoice = db.query(Invoice).filter(Invoice.order_id == order.id).first()
        pickup = order.pickup
        dropoff = order.dropoff
        if public:
            pickup = public_address_snapshot(pickup if isinstance(pickup, dict) else None) or {}
            dropoff = public_address_snapshot(dropoff if isinstance(dropoff, dict) else None) or {}
        branding = self._shipper_branding(db, order) if public else {}
        from porterchain_api.domain.customer_goods import goods_line

        goods = goods_line(order.compliance_metadata if isinstance(order.compliance_metadata, dict) else None)
        if public:
            # Public track page: anyone holding the number sees it — never parcel contents/value.
            goods = {**goods, "goods_summary": None, "declared_value_cents": None}
        return OrderResponse(
            order_id=order.id,
            order_number=order.order_number,
            tracking_number=order.tracking_number,
            state=order.state,
            amount_cents=order.amount_cents,
            currency=order.currency,
            scheduled_at=order.scheduled_at,
            pickup=pickup,
            dropoff=dropoff,
            booking_number=booking.booking_number if booking else None,
            invoice_number=invoice.invoice_number if invoice else None,
            company_name=branding.get("company_name"),
            logo_url=branding.get("logo_url"),
            tracking_page_message=branding.get("tracking_page_message"),
            vehicle_class=goods.get("vehicle_class"),
            booking_mode=goods.get("booking_mode"),
            goods_summary=goods.get("goods_summary"),
            parcel_count=goods.get("parcel_count"),
            declared_value_cents=goods.get("declared_value_cents"),
        )

    def get_order_response_by_tracking(self, db: Session, tracking_number: str) -> OrderResponse | None:
        from porterchain_api.domain.sandbox import order_is_sandbox

        order = self.get_by_tracking(db, tracking_number)
        if not order:
            return None
        # Public surfaces must not resolve test shipments as live capacity.
        if order_is_sandbox(order):
            return None
        return self._order_response_from_order(db, order, public=True)

    def get_order_tracking_response(
        self,
        db: Session,
        settings: Settings,
        tracking_number: str,
    ) -> OrderTrackingResponse | None:
        """Build OrderTrackingResponse for the public order tracking endpoint."""
        from porterchain_api.domain.sandbox import order_is_sandbox

        order = self.get_by_tracking(db, tracking_number)
        if not order or order_is_sandbox(order):
            return None
        live = self.build_public_live_tracking(db, settings, order)
        return OrderTrackingResponse(
            order_id=order.id,
            tracking_number=order.tracking_number,
            state=order.state,
            live_tracking=live,
        )

    def list_customer_orders_response(
        self,
        db: Session,
        *,
        customer_id: str,
        clerk_user_id: str,
        limit: int = 50,
    ) -> list[OrderResponse]:
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise LookupError("customer_not_found")
        if customer.clerk_user_id != clerk_user_id:
            raise PermissionError("forbidden")

        orders = self._orders.list_for_customer(db, customer_id, limit=limit)
        return [self._order_response_from_order(db, o) for o in orders]

    def get_live_tracking(
        self,
        db: Session,
        settings: Settings,
        order: Order,
    ) -> dict | None:
        """Raw live GPS from the assigned driver via the shared facade."""
        return self._facade.fetch_raw(settings, order)

    def get_live_snapshot(
        self,
        db: Session,
        settings: Settings,
        order: Order,
    ) -> dict[str, Any]:
        """Normalized tracking snapshot — identical shape on every portal."""
        return self._facade.live_snapshot(settings, order)

    def build_public_live_tracking(
        self,
        db: Session,
        settings: Settings,
        order: Order,
    ) -> dict[str, Any]:
        """Enriched public snapshot: addresses, map geometry, and ETA."""
        live_raw = self.get_live_tracking(db, settings, order)
        snapshot = build_public_live_tracking(order, live_raw)
        snapshot["branding"] = self._shipper_branding(db, order)
        return snapshot

    def _shipper_branding(self, db: Session, order: Order) -> dict[str, Any]:
        if not order.merchant_id:
            return public_shipper_branding(None)
        merchant = db.query(Merchant).filter(Merchant.id == order.merchant_id).first()
        return public_shipper_branding(merchant)

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
        from porterchain_api.domain.customer_goods import goods_line

        goods = goods_line(order.compliance_metadata if isinstance(order.compliance_metadata, dict) else None)
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
            "created_at": order.created_at.isoformat(),
            "vehicle_class": goods.get("vehicle_class"),
            "booking_mode": goods.get("booking_mode"),
            "goods_summary": goods.get("goods_summary"),
            "parcel_count": goods.get("parcel_count"),
            "declared_value_cents": goods.get("declared_value_cents"),
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
