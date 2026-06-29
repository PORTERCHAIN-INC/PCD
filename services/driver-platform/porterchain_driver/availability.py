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
        online: bool,
        fleetbase_bridge: Any = None,
    ) -> dict:
        from porterchain_api.domain.admin_states import DriverStatus

        if driver.status != DriverStatus.APPROVED.value:
            raise PermissionError("driver_not_approved")
        driver.is_online = online
        driver.availability = "available" if online else "offline"
        if fleetbase_bridge and driver.fleetbase_driver_id:
            fleetbase_bridge.toggle_driver_online(driver.fleetbase_driver_id, online=online)
        db.flush()
        self._emit_availability_event(db, driver, online)
        return self.get_status(driver)

    def accept_assignment(self, db: Session, driver: Any, order_id: str) -> dict:
        from porterchain_api.models import Order
        from porterchain_api.domain.states import OrderState
        from porterchain_api.booking_engine.order_transitions import transition_order_state
        from porterchain_api.booking_engine._core import emit_event
        from porterchain_shared.events.catalog import DomainEventType

        order = db.query(Order).filter(Order.id == order_id, Order.assigned_driver_id == driver.id).first()
        if not order:
            raise LookupError("order_not_found")
        transition_order_state(
            db,
            order,
            OrderState.DRIVER_ACCEPTED,
            event_type=DomainEventType.DRIVER_ACCEPTED,
            actor_type="driver",
            actor_id=driver.id,
        )
        return {"order_id": order.id, "state": order.state}

    def reject_assignment(self, db: Session, driver: Any, order_id: str, *, reason: str = "") -> dict:
        from porterchain_api.models import Order
        from porterchain_api.domain.states import OrderState
        from porterchain_api.booking_engine.order_transitions import transition_order_state
        from porterchain_shared.events.catalog import DomainEventType

        order = db.query(Order).filter(Order.id == order_id, Order.assigned_driver_id == driver.id).first()
        if not order:
            raise LookupError("order_not_found")
        transition_order_state(
            db,
            order,
            OrderState.DRIVER_REJECTED,
            event_type=DomainEventType.DRIVER_REJECTED,
            actor_type="driver",
            actor_id=driver.id,
            payload={"reason": reason},
        )
        order.assigned_driver_id = None
        db.flush()
        return {"order_id": order.id, "state": order.state}

    def _emit_availability_event(self, db: Session, driver: Any, online: bool) -> None:
        from porterchain_api.booking_engine._core import emit_event

        emit_event(
            db,
            event_type="driver.online" if online else "driver.offline",
            aggregate_type="driver",
            aggregate_id=driver.id,
            actor_type="driver",
            actor_id=driver.id,
            payload={"availability": driver.availability},
        )
