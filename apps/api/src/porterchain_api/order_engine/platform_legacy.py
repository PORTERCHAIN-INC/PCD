"""Legacy order platform list/detail queries (backward compatibility)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.booking_models import (
    Booking,
    Customer,
    Invoice,
    Order,
    OrderEvent,
    Payment,
    Quote,
)


class OrderPlatformLegacyMixin:

    def list_orders(
        self,
        db: Session,
        *,
        state: str | None = None,
        search: str | None = None,
        limit: int = 50,
    ) -> list[Order]:
        q = db.query(Order)
        if state:
            q = q.filter(Order.state == state)
        if search:
            pattern = f"%{search}%"
            q = q.filter(
                (Order.tracking_number.ilike(pattern)) | (Order.order_number.ilike(pattern))
            )
        return q.order_by(Order.created_at.desc()).limit(limit).all()

    def get_order(self, db: Session, order_id: str) -> Order | None:
        return db.query(Order).filter(Order.id == order_id).first()

    def order_full_detail(self, db: Session, order_id: str) -> dict | None:
        """Gather every value captured at booking + payment time for one order."""
        order = self.get_order(db, order_id)
        if not order:
            return None

        quote = (
            db.query(Quote).filter(Quote.id == order.quote_id).first()
            if order.quote_id
            else None
        )
        booking = db.query(Booking).filter(Booking.order_id == order.id).first()
        invoice = db.query(Invoice).filter(Invoice.order_id == order.id).first()
        customer = (
            db.query(Customer).filter(Customer.id == order.customer_id).first()
            if order.customer_id
            else None
        )

        payments = (
            db.query(Payment)
            .filter(Payment.order_id == order.id)
            .order_by(Payment.created_at.desc())
            .all()
        )
        if not payments and order.quote_id:
            payments = (
                db.query(Payment)
                .filter(Payment.quote_id == order.quote_id)
                .order_by(Payment.created_at.desc())
                .all()
            )

        return {
            "order": order,
            "quote": quote,
            "booking": booking,
            "invoice": invoice,
            "customer": customer,
            "payments": payments,
        }

    def order_timeline(self, db: Session, order_id: str) -> list[OrderEvent]:
        return (
            db.query(OrderEvent)
            .filter(OrderEvent.order_id == order_id)
            .order_by(OrderEvent.occurred_at.asc())
            .all()
        )

    def list_invoices(self, db: Session, *, limit: int = 50) -> list[Invoice]:
        return db.query(Invoice).order_by(Invoice.created_at.desc()).limit(limit).all()
