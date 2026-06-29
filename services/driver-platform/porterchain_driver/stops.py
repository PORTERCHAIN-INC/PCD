"""Driver stops & routes — today's jobs, arrive, deliver, exceptions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from porterchain_driver.types import RouteView, StopView

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


_ACTIVE_STATES = {
    "DRIVER_ASSIGNED",
    "DRIVER_ACCEPTED",
    "DRIVER_EN_ROUTE",
    "AT_PICKUP",
    "PICKED_UP",
    "IN_TRANSIT",
    "AT_DESTINATION",
    "DELIVERED",
}


class StopsService:
    def today_stops(self, db: Session, driver_id: str) -> list[StopView]:
        return self._stops_for_orders(self._today_orders(db, driver_id))

    def stops_for_route(self, db: Session, driver_id: str, route_id: str) -> list[StopView]:
        if route_id.startswith("route-"):
            return self.today_stops(db, driver_id)
        return self._stops_for_orders(self._orders_for_driver(db, driver_id))

    def assigned_route(self, db: Session, driver: Any) -> RouteView | None:
        stops = self.today_stops(db, driver.id)
        if not stops:
            return None
        today = datetime.now(UTC).date().isoformat()
        route_id = f"route-{today}"
        from porterchain_driver.earnings import EarningsService

        return RouteView(
            route_id=route_id,
            driver_id=driver.id,
            status="assigned" if any(s.status not in ("delivered", "POD_COMPLETED") for s in stops) else "completed",
            stops=stops,
            earnings_cents=EarningsService().route_earnings_cents(db, driver.id, route_id),
        )

    def start_route(self, db: Session, driver: Any, route_id: str) -> RouteView:
        route = self.assigned_route(db, driver)
        if not route:
            raise LookupError("route_not_found")
        route.status = "in_progress"
        route.started_at = datetime.now(UTC)
        return route

    def arrive_stop(self, db: Session, driver: Any, stop_id: str, *, fleetbase_bridge: Any = None) -> StopView:
        order = self._order_for_stop(db, driver.id, stop_id)
        from porterchain_api.domain.states import OrderState
        from porterchain_api.booking_engine.order_transitions import transition_order_state

        target = OrderState.AT_PICKUP if stop_id.endswith("-pickup") else OrderState.AT_DESTINATION
        transition_order_state(
            db,
            order,
            target,
            event_type="order.arrived_pickup" if target == OrderState.AT_PICKUP else "order.arrived_destination",
            actor_type="driver",
            actor_id=driver.id,
        )
        return self._order_to_stop(order, stop_id.split("-")[-1])

    def deliver_stop(
        self,
        db: Session,
        driver: Any,
        stop_id: str,
        *,
        fleetbase_bridge: Any = None,
    ) -> StopView:
        order = self._order_for_stop(db, driver.id, stop_id)
        from porterchain_api.domain.states import OrderState
        from porterchain_api.booking_engine.order_transitions import transition_order_state
        from porterchain_driver.earnings import EarningsService

        if stop_id.endswith("-pickup"):
            transition_order_state(
                db, order, OrderState.PICKED_UP, event_type="order.pickup_completed", actor_type="driver", actor_id=driver.id
            )
        else:
            transition_order_state(
                db, order, OrderState.DELIVERED, event_type="order.delivered", actor_type="driver", actor_id=driver.id
            )
            EarningsService().credit_delivery(db, driver, order_id=order.id)
        return self._order_to_stop(order, stop_id.split("-")[-1])

    def report_exception(
        self,
        db: Session,
        driver: Any,
        stop_id: str,
        *,
        exception_type: str,
        notes: str | None = None,
    ) -> dict:
        from porterchain_api.models import OrderException

        order = self._order_for_stop(db, driver.id, stop_id)
        exc = OrderException(
            order_id=order.id,
            type=exception_type,
            status="open",
            reported_by_type="driver",
            reported_by_id=driver.id,
            evidence={"notes": notes or "", "stop_id": stop_id},
        )
        db.add(exc)
        db.flush()
        return {"exception_id": exc.id, "order_id": order.id, "type": exception_type}

    def _today_orders(self, db: Session, driver_id: str) -> list:
        from porterchain_api.models import Order

        start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        return (
            db.query(Order)
            .filter(
                Order.assigned_driver_id == driver_id,
                Order.state.in_(list(_ACTIVE_STATES) + ["DISPATCH_READY", "POD_COMPLETED"]),
                Order.scheduled_at >= start,
            )
            .order_by(Order.scheduled_at.asc())
            .all()
        )

    def _orders_for_driver(self, db: Session, driver_id: str) -> list:
        from porterchain_api.models import Order

        return (
            db.query(Order)
            .filter(Order.assigned_driver_id == driver_id, Order.state.in_(list(_ACTIVE_STATES)))
            .order_by(Order.scheduled_at.asc())
            .all()
        )

    def _order_for_stop(self, db: Session, driver_id: str, stop_id: str):
        from porterchain_api.models import Order

        order_id = stop_id.rsplit("-", 1)[0]
        order = db.query(Order).filter(Order.id == order_id, Order.assigned_driver_id == driver_id).first()
        if not order:
            raise LookupError("stop_not_found")
        return order

    def _stops_for_orders(self, orders: list) -> list[StopView]:
        stops: list[StopView] = []
        for i, order in enumerate(orders):
            stops.append(self._order_to_stop(order, "pickup", sequence=i * 2))
            stops.append(self._order_to_stop(order, "dropoff", sequence=i * 2 + 1))
        return stops

    def _order_to_stop(self, order: Any, stop_type: str, sequence: int = 0) -> StopView:
        addr = order.pickup if stop_type == "pickup" else order.dropoff
        return StopView(
            stop_id=f"{order.id}-{stop_type}",
            order_id=order.id,
            sequence=sequence,
            stop_type=stop_type,
            status=order.state.lower() if hasattr(order.state, "lower") else str(order.state).lower(),
            address=addr or {},
            scheduled_at=order.scheduled_at,
            tracking_number=order.tracking_number,
            order_number=order.order_number or order.tracking_number,
            special_instructions=order.special_instructions,
            otp_required=stop_type == "dropoff",
            pod_required=stop_type == "dropoff",
        )
