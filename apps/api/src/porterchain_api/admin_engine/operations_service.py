"""Dispatch operations — queue, assignment via Fleetbase bridge."""

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminAuditLog, Driver, RouteCenterPlan
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
        from datetime import UTC, datetime

        from porterchain_api.fleetbase_engine.booking_sync_service import BookingSyncService

        plan = db.query(RouteCenterPlan).filter(RouteCenterPlan.id == plan_id).first()
        if not plan:
            raise LookupError("route_plan_not_found")
        driver = db.query(Driver).filter(Driver.id == driver_id).first()
        if not driver:
            raise LookupError("driver_not_found")

        target_ids = order_ids or list(plan.order_ids or [])
        if not target_ids:
            raise ValueError("no_orders_to_assign")

        results: list[dict] = []
        errors: list[dict] = []
        assigned_orders: list[Order] = []

        for oid in target_ids:
            try:
                order = self._assign_driver_no_commit(db, ctx, oid, driver_id)
                assigned_orders.append(order)
                results.append({"order_id": oid, "status": "assigned", "tracking_number": order.tracking_number})
            except LookupError as exc:
                errors.append({"order_id": oid, "error": str(exc)})
            except Exception as exc:  # noqa: BLE001
                errors.append({"order_id": oid, "error": str(exc)})

        plan.driver_id = driver_id
        plan.status = "dispatched"
        plan.dispatched_at = datetime.now(UTC).replace(tzinfo=None)
        db.flush()

        sync = BookingSyncService()
        for order in assigned_orders:
            if driver.fleetbase_driver_id and order.fleetbase_order_id:
                sync.push_driver_assignment(
                    db, settings, order, fleetbase_driver_id=driver.fleetbase_driver_id
                )

        emit_event(
            db,
            event_type="driver.route_assigned",
            aggregate_type="driver",
            aggregate_id=driver_id,
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={
                "driver_id": driver_id,
                "plan_id": plan_id,
                "order_ids": [o.id for o in assigned_orders],
                "stops": plan.stops or [],
            },
        )
        db.add(
            AdminAuditLog(
                actor_user_id=ctx.user.id,
                action="dispatch.batch_assigned",
                resource_type="route_plan",
                resource_id=plan_id,
                payload={"driver_id": driver_id, "order_ids": [o.id for o in assigned_orders]},
            )
        )
        db.commit()

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
