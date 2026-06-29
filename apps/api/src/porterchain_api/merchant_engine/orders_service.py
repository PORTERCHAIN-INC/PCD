"""Merchant order list, search, and tracking."""

from sqlalchemy.orm import Session

from porterchain_api.booking_engine.tracking_service import TrackingService
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.models import Order, OrderEvent


class MerchantOrdersService:
    def __init__(self) -> None:
        self._tracking = TrackingService()

    def list_orders(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        state: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Order]:
        q = db.query(Order).filter(Order.merchant_id == ctx.merchant.id)
        if state:
            q = q.filter(Order.state == state)
        if search:
            pattern = f"%{search}%"
            q = q.filter(
                (Order.tracking_number.ilike(pattern))
                | (Order.order_number.ilike(pattern))
                | (Order.internal_reference.ilike(pattern))
                | (Order.purchase_order_number.ilike(pattern))
            )
        return q.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()

    def get_order(self, db: Session, ctx: MerchantContext, order_id: str) -> Order | None:
        return (
            db.query(Order)
            .filter(Order.id == order_id, Order.merchant_id == ctx.merchant.id)
            .first()
        )

    def get_tracking_timeline(self, db: Session, ctx: MerchantContext, order_id: str) -> list[dict]:
        order = self.get_order(db, ctx, order_id)
        if not order:
            raise LookupError("order_not_found")
        events = (
            db.query(OrderEvent)
            .filter(OrderEvent.order_id == order_id)
            .order_by(OrderEvent.occurred_at.asc())
            .all()
        )
        return [
            {
                "event_type": e.event_type,
                "from_state": e.from_state,
                "to_state": e.to_state,
                "payload": e.payload,
                "occurred_at": e.occurred_at.isoformat(),
            }
            for e in events
        ]

    def get_by_tracking(self, db: Session, ctx: MerchantContext, tracking_number: str) -> Order | None:
        order = self._tracking.get_by_tracking(db, tracking_number)
        if order and order.merchant_id == ctx.merchant.id:
            return order
        return None
