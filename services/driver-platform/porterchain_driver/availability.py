"""Driver availability — online/offline, schedule."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class AvailabilityService:
    def get_status(self, driver: Any) -> dict:
        return {
            "is_online": bool(driver.is_online),
            "availability": driver.availability or "offline",
            "fleetbase_driver_id": driver.fleetbase_driver_id,
        }

    def set_online(
        self,
        db: Session,
        driver: Any,
        *,
        online: bool) -> dict:
        from porterchain_driver.shift import ShiftService

        mode = "online" if online else "offline"
        ShiftService().set_availability(db, driver, mode)
        return self.get_status(driver)

    def accept_assignment(
        self,
        db: Session,
        driver: Any,
        order_id: str,
    ) -> dict:
        from porterchain_api.booking_models import Order
        from porterchain_api.domain.states import OrderState
        from porterchain_api.booking_engine.order_transitions import transition_order_state
        from porterchain_api.booking_engine._core import emit_event
        from porterchain_shared.events.catalog import DomainEventType

        order = db.query(Order).filter(Order.id == order_id, Order.assigned_driver_id == driver.id).first()
        if not order:
            raise LookupError("order_not_found")
        if order.state not in {OrderState.DRIVER_ASSIGNED.value, OrderState.DRIVER_ACCEPTED.value}:
            raise ValueError("job_not_awaiting_response")
        transition_order_state(
            db,
            order,
            OrderState.DRIVER_ACCEPTED,
            event_type=DomainEventType.DRIVER_ACCEPTED,
            actor_type="driver",
            actor_id=driver.id)
        try:
            from porterchain_driver.jobs import JobsService

            JobsService().optimize_route(db, driver, insert_order_id=order.id)
        except Exception:  # noqa: BLE001 — accept must succeed even if optimize queues fail
            pass
        return {"order_id": order.id, "state": order.state}

    def reject_assignment(
        self,
        db: Session,
        driver: Any,
        order_id: str,
        *,
        reason: str = "") -> dict:
        from porterchain_api.booking_models import Order
        from porterchain_api.domain.states import OrderState
        from porterchain_api.booking_engine.order_transitions import transition_order_state
        from porterchain_shared.events.catalog import DomainEventType

        order = db.query(Order).filter(Order.id == order_id, Order.assigned_driver_id == driver.id).first()
        if not order:
            raise LookupError("order_not_found")
        if order.state != OrderState.DRIVER_ASSIGNED.value:
            raise ValueError("job_not_awaiting_response")
        transition_order_state(
            db,
            order,
            OrderState.DRIVER_REJECTED,
            event_type=DomainEventType.DRIVER_REJECTED,
            actor_type="driver",
            actor_id=driver.id,
            payload={"reason": reason})
        fleetbase_order_id = order.fleetbase_order_id
        order.assigned_driver_id = None
        db.flush()
        return {"order_id": order.id, "state": order.state}
