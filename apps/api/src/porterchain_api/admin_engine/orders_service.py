"""Admin order management."""

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.booking_engine.order_transitions import transition_order_state
from porterchain_api.domain.states import OrderState, QuoteState
from porterchain_api.models import Booking, Invoice, Order, OrderEvent, Quote


class AdminOrdersService:
    def list_quotes(self, db: Session, *, state: str | None = None, limit: int = 50) -> list[Quote]:
        q = db.query(Quote)
        if state:
            q = q.filter(Quote.state == state)
        return q.order_by(Quote.created_at.desc()).limit(limit).all()

    def list_bookings(self, db: Session, *, limit: int = 50) -> list[Booking]:
        return db.query(Booking).order_by(Booking.created_at.desc()).limit(limit).all()

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

    def order_timeline(self, db: Session, order_id: str) -> list[OrderEvent]:
        return (
            db.query(OrderEvent)
            .filter(OrderEvent.order_id == order_id)
            .order_by(OrderEvent.occurred_at.asc())
            .all()
        )

    def list_invoices(self, db: Session, *, limit: int = 50) -> list[Invoice]:
        return db.query(Invoice).order_by(Invoice.created_at.desc()).limit(limit).all()

    def force_transition(
        self,
        db: Session,
        ctx: AdminContext,
        order_id: str,
        to_state: str,
    ) -> Order:
        order = self.get_order(db, order_id)
        if not order:
            raise LookupError("order_not_found")
        return transition_order_state(
            db,
            order,
            OrderState(to_state),
            event_type="order.admin_override",
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={"forced": True},
        )

    def pending_quotes_count(self, db: Session) -> int:
        return db.query(Quote).filter(Quote.state == QuoteState.QUOTE.value).count()
