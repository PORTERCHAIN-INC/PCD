"""Dispatch operations — queue and assignment."""

from porterchain_shared.events.catalog import DomainEventType
from sqlalchemy.orm import Session

from porterchain_api.admin_engine import events as E
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminAuditLog, Driver
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.compliance_metadata import (
    requires_medical_certified,
)
from porterchain_api.booking_engine.order_transitions import transition_order_state
from porterchain_api.booking_models import Order
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.domain.states import OrderState
from porterchain_api.order_engine.buckets import dispatch_queue_sort_key

# States where a driver already owns the job and the order cannot go back to DRIVER_ASSIGNED.
# Reassigning here is a handoff: same state, new driver (e.g. delivery leg after pickup / hub).
HANDOFF_STATES = frozenset({
    OrderState.DRIVER_ACCEPTED.value,
    OrderState.DRIVER_EN_ROUTE.value,
    OrderState.AT_PICKUP.value,
    OrderState.PICKED_UP.value,
    OrderState.IN_TRANSIT.value,
    OrderState.AT_DESTINATION.value,
})


ONBOARD_STATES = frozenset({
    OrderState.PICKED_UP.value, OrderState.IN_TRANSIT.value, OrderState.AT_DESTINATION.value,
})


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
        if order.state in HANDOFF_STATES and order.assigned_driver_id:
            # Already accepted / on the road / picked up: the state machine has no way back to
            # DRIVER_ASSIGNED, so hand the job to the new driver in place (delivery leg).
            order = self._handoff_driver_no_commit(db, ctx, order, driver_id)
        else:
            order = self._assign_driver_no_commit(db, ctx, order_id, driver_id)
        db.commit()
        db.refresh(order)
        from porterchain_api.dispatch_engine.optimize_run_store import (
            fleet_optimize_open,
        )

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
            from porterchain_driver.jobs import JobsService

            from porterchain_api.user_models import Driver

            driver = db.query(Driver).filter(Driver.id == driver_id).first()
            if driver is not None:
                JobsService().optimize_route(db, driver, insert_order_id=insert_order_id)
        except Exception:  # noqa: BLE001 — assign must succeed even if optimize queues fail
            pass

    @staticmethod
    def release_assignment_no_commit(db: Session, ctx: AdminContext, order: Order, *, plan_id: str) -> None:
        """Undo a plan assignment: back to the dispatch pool. Caller guarantees DRIVER_ASSIGNED.

        Canonical path (ASSIGNED → REJECTED → DISPATCH_READY) tagged ``order.plan_undo`` so it never
        counts as a driver rejection.
        """
        actor = getattr(getattr(ctx, "user", None), "id", None)
        payload = {"driver_id": order.assigned_driver_id, "plan_id": plan_id, "reason": "plan_undo"}
        for to in (OrderState.DRIVER_REJECTED, OrderState.DISPATCH_READY):
            transition_order_state(db, order, to, event_type="order.plan_undo",
                                   actor_type="admin", actor_id=actor, payload=payload)
        order.assigned_driver_id = None
        db.add(AdminAuditLog(actor_user_id=actor, action="dispatch.plan_undo", resource_type="order",
                             resource_id=order.id, payload=payload))
        # Tell the driver (push + in-app via the notification router) — the job left their list.
        emit_event(
            db,
            event_type=DomainEventType.DRIVER_JOB_REMOVED,
            aggregate_type="order",
            aggregate_id=order.id,
            actor_type="admin",
            actor_id=actor,
            payload={**payload, "order_id": order.id, "order_number": order.order_number,
                     "tracking_number": order.tracking_number, "driver_deep_link": "/jobs"},
        )
        db.commit()

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
        from porterchain_api.admin_engine.control_tower.scoring import (
            driver_verification_gap,
        )

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

    @staticmethod
    def _check_driver(db: Session, order: Order, driver_id: str) -> Driver:
        driver = db.query(Driver).filter(Driver.id == driver_id).first()
        if not driver:
            raise LookupError("driver_not_found")
        if driver.status != DriverStatus.APPROVED.value:
            raise ValueError("driver_not_approved")
        from porterchain_api.admin_engine.control_tower.scoring import (
            driver_verification_gap,
        )

        gap = driver_verification_gap(driver)
        if gap:
            raise ValueError(gap)
        if requires_medical_certified(order.compliance_metadata) and not driver.medical_transport_certified:
            raise ValueError("driver_not_medical_certified")
        return driver

    def _handoff_driver_no_commit(self, db: Session, ctx: AdminContext, order: Order, driver_id: str) -> Order:
        """Reassign an in-flight order (accepted → at destination) without changing its state.

        Old driver gets ``job_removed``; new driver gets ``job_handoff`` (push + in-app); the
        customer/merchant get the normal tracking-only ``driver_assigned`` notice (no driver
        contact details — merchants/customers only ever see the driver's name on the order).
        Pending plan stops for this order move from the old driver's route to the new one.
        """
        from porterchain_api.booking_models import OrderEvent

        old_driver_id = order.assigned_driver_id
        if old_driver_id == driver_id:
            raise ValueError("driver_already_assigned")
        self._check_driver(db, order, driver_id)
        order.assigned_driver_id = driver_id
        leg = "delivery" if order.state in ONBOARD_STATES else "pickup"
        payload = {
            "order_id": order.id,
            "order_number": order.order_number,
            "tracking_number": order.tracking_number,
            "customer_id": order.customer_id,
            "merchant_id": order.merchant_id,
            "from_driver_id": old_driver_id,
            "driver_id": driver_id,
            "state": order.state,
            "leg": leg,
            "handoff": True,
            "driver_deep_link": f"/jobs/{order.id}",
        }
        db.add(OrderEvent(order_id=order.id, event_type="order.driver_handoff", from_state=order.state,
                          to_state=order.state, actor_type="admin", actor_id=ctx.user.id,
                          correlation_id=order.quote_id, payload=payload))
        db.add(AdminAuditLog(actor_user_id=ctx.user.id, action="dispatch.reassigned", resource_type="order",
                             resource_id=order.id,
                             payload={"from_driver_id": old_driver_id, "driver_id": driver_id,
                                      "state": order.state, "leg": leg}))
        common = {"aggregate_type": "order", "aggregate_id": order.id, "actor_type": "admin",
                  "actor_id": ctx.user.id}
        if old_driver_id:
            emit_event(db, event_type=DomainEventType.DRIVER_JOB_REMOVED,
                       payload={**payload, "driver_id": old_driver_id, "reason": "reassigned",
                                "driver_deep_link": "/jobs"}, **common)
        emit_event(db, event_type=DomainEventType.DRIVER_HANDOFF, payload=payload, **common)
        emit_event(db, event_type=E.DISPATCH_ASSIGNED, payload=payload, **common)
        self._move_plan_stops(db, order.id, old_driver_id, driver_id)
        db.flush()
        return order

    @staticmethod
    def _move_plan_stops(db: Session, order_id: str, old_driver_id: str | None, new_driver_id: str) -> None:
        """Best-effort: move this order's not-done stops from the old driver's route to the new one."""
        if not old_driver_id:
            return
        from porterchain_api.dispatch_engine.driver_route import DriverRouteService
        from porterchain_api.dispatch_engine.models import DispatchRoute

        routes = DriverRouteService()
        src = routes.current_route(db, old_driver_id)
        if src is None:
            return
        dst = routes.current_route(db, new_driver_id)
        done = routes.done_keys(db, [r.id for r in (src, dst) if r is not None])
        moving = [s for s in (src.stops or []) if s.get("order_id") == order_id and s.get("key") not in done]
        if not moving:
            return
        src.stops = [s for s in src.stops if s not in moving]
        if dst is None:
            dst = DispatchRoute(plan_id=src.plan_id, vehicle_id=f"v-{new_driver_id}", driver_id=new_driver_id,
                                vehicle_class=src.vehicle_class, stops=[], status=src.status)
            db.add(dst)
        dst.stops = list(dst.stops or []) + moving

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
