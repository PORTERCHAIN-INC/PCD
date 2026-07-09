"""Dispatch operations — queue, assignment via Fleetbase bridge."""

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminAuditLog, Driver
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.compliance_metadata import requires_medical_certified
from porterchain_api.admin_engine import events as E
from porterchain_api.booking_engine.order_transitions import transition_order_state
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderState
from porterchain_api.models import Order, OrderException
from porterchain_api.order_engine.buckets import dispatch_queue_sort_key


class AdminOperationsService:
    def dispatch_queue(self, db: Session, *, limit: int = 50) -> list[Order]:
        rows = (
            db.query(Order)
            .filter(Order.state == OrderState.DISPATCH_READY.value)
            .all()
        )
        rows.sort(key=dispatch_queue_sort_key)
        return rows[:limit]

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
        driver = db.query(Driver).filter(Driver.id == driver_id).first()
        if not driver:
            raise LookupError("driver_not_found")
        if requires_medical_certified(order.compliance_metadata) and not driver.medical_transport_certified:
            raise ValueError("driver_not_medical_certified")
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

    def assign_batch(
        self,
        db: Session,
        settings: Settings,
        ctx: AdminContext,
        *,
        plan_id: str,
        driver_id: str,
        order_ids: list[str] | None = None,
    ) -> dict:
        """Assign a batch of orders to one driver.

        Each order is assigned inside its own savepoint so a single failure
        (missing order, invalid transition) is reported per-order without
        aborting the whole batch.
        """
        ids = order_ids or []
        results: list[dict] = []
        errors: list[dict] = []
        for order_id in ids:
            try:
                with db.begin_nested():
                    order = self._assign_driver_no_commit(db, ctx, order_id, driver_id)
                results.append(
                    {
                        "order_id": order_id,
                        "status": order.state,
                        "tracking_number": getattr(order, "tracking_number", None),
                    }
                )
            except (LookupError, ValueError) as exc:
                errors.append({"order_id": order_id, "error": str(exc)})
        if results:
            db.commit()
        else:
            db.rollback()
        return {
            "plan_id": plan_id,
            "driver_id": driver_id,
            "assigned_count": len(results),
            "results": results,
            "errors": errors,
        }

    def live_map_snapshot(self, db: Session) -> dict:
        from porterchain_api.admin_engine.live_map_service import LiveMapService

        return LiveMapService().snapshot(db)
