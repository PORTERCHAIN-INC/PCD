"""Dispatch operations — queue, assignment via Fleetbase bridge."""

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminAuditLog, Driver
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.admin_engine import events as E
from porterchain_api.booking_engine.order_transitions import transition_order_state
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderState
from porterchain_api.models import Order, OrderException


class AdminOperationsService:
    def dispatch_queue(self, db: Session, *, limit: int = 50) -> list[Order]:
        return (
            db.query(Order)
            .filter(Order.state == OrderState.DISPATCH_READY.value)
            .order_by(Order.scheduled_at.asc())
            .limit(limit)
            .all()
        )

    def exception_queue(self, db: Session, *, limit: int = 50) -> list[OrderException]:
        return (
            db.query(OrderException)
            .filter(OrderException.status == "open")
            .order_by(OrderException.created_at.desc())
            .limit(limit)
            .all()
        )

    def assign_driver(
        self,
        db: Session,
        settings: Settings,
        ctx: AdminContext,
        order_id: str,
        driver_id: str,
    ) -> Order:
        order = self._assign_driver_no_commit(db, ctx, order_id, driver_id)
        db.commit()
        db.refresh(order)
        return order

    def _assign_driver_no_commit(
        self,
        db: Session,
        ctx: AdminContext,
        order_id: str,
        driver_id: str,
    ) -> Order:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise LookupError("order_not_found")
        transition_order_state(
            db,
            order,
            OrderState.DRIVER_ASSIGNED,
            event_type="order.driver_assigned",
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={"driver_id": driver_id},
        )
        order.assigned_driver_id = driver_id
        db.flush()
        db.add(
            AdminAuditLog(
                actor_user_id=ctx.user.id,
                action="dispatch.assigned",
                resource_type="order",
                resource_id=order_id,
                payload={"driver_id": driver_id},
            )
        )
        emit_event(
            db,
            event_type=E.DISPATCH_ASSIGNED,
            aggregate_type="order",
            aggregate_id=order_id,
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={"driver_id": driver_id},
        )
        return order

    def live_map_snapshot(self, db: Session) -> dict:
        from porterchain_api.admin_engine.live_map_service import LiveMapService

        return LiveMapService().snapshot(db)
