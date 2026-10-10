"""Dispatch operations — queue and assignment."""

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
from porterchain_api.booking_models import Order
from porterchain_api.order_engine.buckets import dispatch_queue_sort_key


class AdminOperationsService:
    def dispatch_queue(self, db: Session, *, limit: int = 50) -> list[Order]:
        rows = (
            db.query(Order)
            .filter(
                Order.is_sandbox.is_(False),
                Order.state == OrderState.DISPATCH_READY.value,
            )
            .all()
        )
        rows.sort(key=dispatch_queue_sort_key)
        return rows[:limit]

    def assign_driver(
        self,
        db: Session,
        settings: Settings,
        ctx: AdminContext,
        order_id: str,
        driver_id: str,
    ) -> Order:
        from porterchain_api.domain.sandbox import order_is_sandbox

        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise LookupError("order_not_found")
        if order_is_sandbox(order):
            raise ValueError("sandbox_orders_block_live_assign")
        order = self._assign_driver_no_commit(db, ctx, order_id, driver_id)
        db.commit()
        db.refresh(order)
        from porterchain_api.dispatch_engine.optimize_run_store import fleet_optimize_open

        if not fleet_optimize_open():
            self._enqueue_driver_book_optimize(db, driver_id, insert_order_id=order.id)
        return order

    @staticmethod
    def _enqueue_driver_book_optimize(  # dispatch-guard:ok — queues the day plan, no local sequencing
        db: Session,
        driver_id: str,
        *,
        insert_order_id: str | None = None,
    ) -> None:
        """Best-effort re-sequence of a driver's book after assignment."""
        try:
            from porterchain_api.user_models import Driver
            from porterchain_driver.jobs import JobsService

            driver = db.query(Driver).filter(Driver.id == driver_id).first()
            if driver is not None:
                JobsService().optimize_route(db, driver, insert_order_id=insert_order_id)
        except Exception:  # noqa: BLE001 — assign must succeed even if optimize queues fail
            pass

    def _assign_driver_no_commit(
        self,
        db: Session,
        ctx: AdminContext,
        order_id: str,
        driver_id: str,
    ) -> Order:
        from porterchain_api.domain.sandbox import order_is_sandbox

        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise LookupError("order_not_found")
        if order_is_sandbox(order):
            raise ValueError("sandbox_orders_block_live_assign")
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
        # Bind driver before publish so job list + hydrate see assigned_driver_id
        # when the phone rings (order.driver_assigned → job_assigned push).
        order.assigned_driver_id = driver_id
        db.flush()
        assign_payload = {
            "driver_id": driver_id,
            "order_id": order.id,
            "order_number": order.order_number,
            "tracking_number": order.tracking_number,
            "customer_id": order.customer_id,
            "merchant_id": order.merchant_id,
            "driver_deep_link": f"/jobs/{order.id}",
        }
        transition_order_state(
            db,
            order,
            OrderState.DRIVER_ASSIGNED,
            event_type="order.driver_assigned",
            actor_type="admin",
            actor_id=ctx.user.id,
            payload=assign_payload,
        )
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
            payload=assign_payload,
        )
        return order

    def process_sync_retry(self, db: Session, *, limit: int = 1) -> dict:
        del db, limit
        return {"processed": 0, "failed": 0, "skipped": 0}

    def requeue_sync_job(self, db: Session, job_id: str) -> dict:
        del db, job_id
        raise LookupError("job_not_found")

    @staticmethod
    def queue_depths_snapshot() -> dict:
        from porterchain_shared.queue.publisher import queue_depths

        return {"depths": queue_depths()}
