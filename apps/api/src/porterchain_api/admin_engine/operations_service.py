"""Dispatch operations — queue, assignment via Fleetbase bridge."""

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminAuditLog, Driver
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.compliance_metadata import requires_medical_certified
from porterchain_api.admin_engine import events as E
from porterchain_api.booking_engine.order_transitions import transition_order_state
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import DriverStatus
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
        driver = db.query(Driver).filter(Driver.id == driver_id).first()
        if driver and settings.fleetbase_dispatch_bridge:
            from porterchain_api.fleetbase_engine import BookingSyncService

            BookingSyncService().push_driver_assignment(
                db,
                settings,
                order,
                fleetbase_driver_id=driver.fleetbase_driver_id,
            )
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
        if driver.status != DriverStatus.APPROVED.value:
            raise ValueError("driver_not_approved")
        # D-27: hard-gate verification beyond medical (license / insurance / background).
        from porterchain_api.admin_engine.control_tower.scoring import driver_verification_gap

        gap = driver_verification_gap(driver)
        if gap:
            raise ValueError(gap)
        if requires_medical_certified(order.compliance_metadata) and not driver.medical_transport_certified:
            raise ValueError("driver_not_medical_certified")
        transition_order_state(
            db,
            order,
            OrderState.DRIVER_ASSIGNED,
            event_type="order.driver_assigned",
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={
                "driver_id": driver_id,
                "order_id": order.id,
                "order_number": order.order_number,
                "tracking_number": order.tracking_number,
                "customer_id": order.customer_id,
                "merchant_id": order.merchant_id,
            },
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
            payload={
                "driver_id": driver_id,
                "order_id": order.id,
                "order_number": order.order_number,
                "tracking_number": order.tracking_number,
                "customer_id": order.customer_id,
                "merchant_id": order.merchant_id,
            },
        )
        return order
