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

_PLAN_STATUSES = ("dispatched", "active")

# Driver stop actions advance through valid lifecycle steps (ORDER_LIFECYCLE.md).
_PICKUP_ARRIVAL_STEPS: list[tuple[str, str]] = [
    ("DRIVER_ACCEPTED", "order.driver_accepted"),
    ("DRIVER_EN_ROUTE", "order.driver_en_route"),
    ("AT_PICKUP", "order.arrived_pickup"),
]
_DELIVERY_ARRIVAL_STEPS: list[tuple[str, str]] = [
    ("IN_TRANSIT", "order.in_transit"),
    ("AT_DESTINATION", "order.near_delivery"),
]
_PICKUP_COMPLETE_STEPS: list[tuple[str, str]] = [
    *_PICKUP_ARRIVAL_STEPS,
    ("PICKED_UP", "order.pickup_completed"),
]
_DELIVERY_COMPLETE_STEPS: list[tuple[str, str]] = [
    *_DELIVERY_ARRIVAL_STEPS,
    ("DELIVERED", "order.delivered"),
]


_PICKUP_DONE_STATES = frozenset(
    {
        "PICKED_UP",
        "IN_TRANSIT",
        "AT_DESTINATION",
        "DELIVERED",
        "POD_COMPLETED",
        "INVOICED",
        "CLOSED",
    }
)


def _validate_stop_action(order: Any, stop_id: str, action: str) -> None:
    from porterchain_api.order_engine.buckets import DELIVERY_LEG, PICKUP_LEG

    state = str(order.state).upper()
    is_pickup = stop_id.endswith("-pickup")

    if is_pickup:
        if state in _PICKUP_DONE_STATES:
            raise ValueError("pickup_already_completed")
        if action == "deliver" and state not in PICKUP_LEG and state != "DRIVER_ASSIGNED":
            raise ValueError("pickup_already_completed")
    else:
        if state in PICKUP_LEG or state in ("BOOKED", "DISPATCH_READY", "DRIVER_ASSIGNED"):
            raise ValueError("pickup_required")
        if action == "deliver" and state == "DELIVERED":
            return
        if action == "arrive" and state in DELIVERY_LEG:
            return


def _validate_current_stop(db: Session, driver: Any, stop_id: str) -> None:
    from porterchain_driver.next_stop import NextStopResolver

    next_stop = NextStopResolver().resolve(db, driver)
    if not next_stop:
        return
    order_id = stop_id.rsplit("-", 1)[0]
    if next_stop.get("order_id") != order_id:
        raise ValueError("not_current_stop")


def _record_stop_completion(db: Session, driver_id: str, order_id: str, stop_type: str) -> None:
    from porterchain_api.driver_models import DriverStopMeta

    now = datetime.now(UTC).isoformat()
    row = db.query(DriverStopMeta).filter(DriverStopMeta.order_id == order_id).first()
    meta = dict(row.meta or {}) if row else {}
    if stop_type == "pickup":
        meta["pickup_completed_at"] = now
    else:
        meta["delivery_completed_at"] = now
    if row:
        row.meta = meta
        row.driver_id = driver_id
    else:
        db.add(DriverStopMeta(order_id=order_id, driver_id=driver_id, meta=meta))
    db.flush()


def _apply_state_chain(
    db: Session,
    order: Any,
    steps: list[tuple[str, str]],
    *,
    actor_type: str,
    actor_id: str,
) -> None:
    from porterchain_api.domain.states import OrderState, can_transition_order
    from porterchain_api.booking_engine.order_transitions import transition_order_state

    if not steps:
        return

    final = OrderState(steps[-1][0])
    current = OrderState(order.state)
    if current == final:
        return

    start = 0
    for i, (state_value, _) in enumerate(steps):
        step_state = OrderState(state_value)
        if current == step_state:
            start = i + 1
            break
        if can_transition_order(current, step_state):
            start = i
            break
    else:
        if current == OrderState.DRIVER_ASSIGNED and can_transition_order(current, OrderState(steps[0][0])):
            start = 0
        else:
            raise ValueError(f"Invalid order transition {current} -> {final}")

    for state_value, event_type in steps[start:]:
        target = OrderState(state_value)
        current = OrderState(order.state)
        if current == target:
            continue
        transition_order_state(
            db,
            order,
            target,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
        )


class StopsService:
    def today_stops(self, db: Session, driver_id: str) -> list[StopView]:
        plan = self._active_plan(db, driver_id)
        if plan and plan.stops:
            return self._stops_from_plan(db, plan)
        return self._stops_for_orders(self._today_orders(db, driver_id))

    def stops_for_route(self, db: Session, driver_id: str, route_id: str) -> list[StopView]:
        if route_id.startswith("route-"):
            return self.today_stops(db, driver_id)
        plan = self._plan_by_id(db, driver_id, route_id)
        if plan and plan.stops:
            return self._stops_from_plan(db, plan)
        return self._stops_for_orders(self._orders_for_driver(db, driver_id))

    def assigned_route(self, db: Session, driver: Any) -> RouteView | None:
        plan = self._active_plan(db, driver.id)
        if plan and plan.stops:
            stops = self._stops_from_plan(db, plan)
            if not stops:
                return None
            from porterchain_driver.earnings import EarningsService

            return RouteView(
                route_id=plan.id,
                driver_id=driver.id,
                status="assigned" if any(s.status not in ("delivered", "POD_COMPLETED") for s in stops) else "completed",
                stops=stops,
                earnings_cents=EarningsService().route_earnings_cents(db, driver.id, plan.id),
            )

        stops = self._stops_for_orders(self._today_orders(db, driver.id))
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

    def start_route(
        self, db: Session, driver: Any, route_id: str, *, fleetbase_bridge: Any = None
    ) -> RouteView:
        route = self.assigned_route(db, driver)
        if not route:
            raise LookupError("route_not_found")
        route.status = "in_progress"
        route.started_at = datetime.now(UTC)
        if fleetbase_bridge:
            for order in self._today_orders(db, driver.id):
                if order.fleetbase_order_id:
                    fleetbase_bridge.sync_order_state(order.fleetbase_order_id, "DRIVER_EN_ROUTE")
        from porterchain_api.booking_engine._core import emit_event

        emit_event(
            db,
            event_type="driver.route_changed",
            aggregate_type="driver",
            aggregate_id=driver.id,
            actor_type="driver",
            actor_id=driver.id,
            payload={
                "driver_id": driver.id,
                "route_id": route.route_id,
                "stops_count": len(route.stops),
            },
        )
        return route

    def arrive_stop(
        self,
        db: Session,
        driver: Any,
        stop_id: str,
        *,
        fleetbase_bridge: Any = None,
        enforce_sequence: bool = True,
    ) -> StopView:
        order = self._order_for_stop(db, driver.id, stop_id)
        _validate_stop_action(order, stop_id, "arrive")
        if enforce_sequence:
            _validate_current_stop(db, driver, stop_id)
        steps = _PICKUP_ARRIVAL_STEPS if stop_id.endswith("-pickup") else _DELIVERY_ARRIVAL_STEPS
        _apply_state_chain(db, order, steps, actor_type="driver", actor_id=driver.id)
        if fleetbase_bridge and order.fleetbase_order_id:
            from porterchain_api.domain.states import OrderState

            target = OrderState(steps[-1][0])
            fleetbase_bridge.sync_order_state(order.fleetbase_order_id, target.value)
        stop_type = stop_id.split("-")[-1]
        if stop_type == "pickup":
            stop_type = "pickup"
        else:
            stop_type = "dropoff"
        return self._order_to_stop(order, stop_type)

    def deliver_stop(
        self,
        db: Session,
        driver: Any,
        stop_id: str,
        *,
        fleetbase_bridge: Any = None,
        enforce_sequence: bool = True,
        auto_reoptimize: bool = False,
    ) -> StopView:
        order = self._order_for_stop(db, driver.id, stop_id)
        from porterchain_api.domain.states import OrderState
        from porterchain_driver.earnings import EarningsService

        _validate_stop_action(order, stop_id, "deliver")
        if enforce_sequence:
            _validate_current_stop(db, driver, stop_id)

        is_pickup = stop_id.endswith("-pickup")
        if is_pickup:
            steps = _PICKUP_COMPLETE_STEPS
            _apply_state_chain(db, order, steps, actor_type="driver", actor_id=driver.id)
            target = OrderState.PICKED_UP
            _record_stop_completion(db, driver.id, order.id, "pickup")
        else:
            steps = _DELIVERY_COMPLETE_STEPS
            _apply_state_chain(db, order, steps, actor_type="driver", actor_id=driver.id)
            target = OrderState.DELIVERED
            _record_stop_completion(db, driver.id, order.id, "dropoff")
            EarningsService().credit_delivery(db, driver, order_id=order.id)
        if fleetbase_bridge and order.fleetbase_order_id:
            fleetbase_bridge.sync_order_state(order.fleetbase_order_id, target.value)
        if auto_reoptimize:
            from porterchain_driver.route_optimizer import DriverRouteOptimizer

            DriverRouteOptimizer().reoptimize_remaining(db, driver, stop_id)
        stop_type = "pickup" if is_pickup else "dropoff"
        return self._order_to_stop(order, stop_type)

    def report_exception(
        self,
        db: Session,
        driver: Any,
        stop_id: str,
        *,
        exception_type: str,
        notes: str | None = None,
        fleetbase_bridge: Any = None,
    ) -> dict:
        from porterchain_api.booking_engine._core import emit_event
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
        if fleetbase_bridge and order.fleetbase_order_id:
            fleetbase_bridge.sync_order_state(order.fleetbase_order_id, "FAILED")
        emit_event(
            db,
            event_type="incident.reported",
            aggregate_type="order",
            aggregate_id=order.id,
            actor_type="driver",
            actor_id=driver.id,
            payload={
                "order_id": order.id,
                "driver_id": driver.id,
                "exception_type": exception_type,
                "exception_id": exc.id,
                "notes": notes or "",
            },
        )
        return {"exception_id": exc.id, "order_id": order.id, "type": exception_type}

    # API router aliases (driver.py)
    def assignedroute_response(self, db: Session, driver: Any) -> RouteView | None:
        return self.assigned_route(db, driver)

    def startroute_response(
        self, db: Session, driver: Any, route_id: str, *, fleetbase_bridge: Any = None
    ) -> RouteView:
        return self.start_route(db, driver, route_id, fleetbase_bridge=fleetbase_bridge)

    def stops_forroute_response(self, db: Session, driver_id: str, route_id: str) -> list[StopView]:
        return self.stops_for_route(db, driver_id, route_id)

    def arrivestop_response(
        self,
        db: Session,
        driver: Any,
        stop_id: str,
        *,
        fleetbase_bridge: Any = None,
        enforce_sequence: bool = True,
    ) -> StopView:
        return self.arrive_stop(
            db,
            driver,
            stop_id,
            fleetbase_bridge=fleetbase_bridge,
            enforce_sequence=enforce_sequence,
        )

    def deliverstop_response(
        self,
        db: Session,
        driver: Any,
        stop_id: str,
        *,
        fleetbase_bridge: Any = None,
        enforce_sequence: bool = True,
        auto_reoptimize: bool = False,
    ) -> StopView:
        return self.deliver_stop(
            db,
            driver,
            stop_id,
            fleetbase_bridge=fleetbase_bridge,
            enforce_sequence=enforce_sequence,
            auto_reoptimize=auto_reoptimize,
        )

    def _active_plan(self, db: Session, driver_id: str):
        try:
            from porterchain_api.admin_models import RouteCenterPlan
        except ImportError:
            # Route Center tables removed — optimization lives in Fleetbase/VROOM.
            return None

        return (
            db.query(RouteCenterPlan)
            .filter(
                RouteCenterPlan.driver_id == driver_id,
                RouteCenterPlan.status.in_(_PLAN_STATUSES),
            )
            .order_by(RouteCenterPlan.dispatched_at.desc())
            .first()
        )

    def _plan_by_id(self, db: Session, driver_id: str, plan_id: str):
        try:
            from porterchain_api.admin_models import RouteCenterPlan
        except ImportError:
            return None

        return (
            db.query(RouteCenterPlan)
            .filter(
                RouteCenterPlan.id == plan_id,
                RouteCenterPlan.driver_id == driver_id,
            )
            .first()
        )

    def _stops_from_plan(self, db: Session, plan: Any) -> list[StopView]:
        from porterchain_api.models import Order

        order_ids = list(plan.order_ids or [])
        orders_by_id = {
            o.id: o
            for o in db.query(Order).filter(Order.id.in_(order_ids)).all()
        } if order_ids else {}

        stops: list[StopView] = []
        sorted_stops = sorted(plan.stops or [], key=lambda s: int(s.get("sequence") or 0))
        for stop in sorted_stops:
            oid = stop.get("order_id")
            order = orders_by_id.get(oid)
            if not order:
                continue
            stop_type_raw = stop.get("type") or "delivery"
            stop_type = "pickup" if stop_type_raw == "pickup" else "dropoff"
            sequence = int(stop.get("sequence") or len(stops))
            view = self._order_to_stop(order, stop_type, sequence=sequence - 1)
            addr = stop.get("location") or (order.pickup if stop_type == "pickup" else order.dropoff)
            if addr:
                view = StopView(
                    stop_id=view.stop_id,
                    order_id=view.order_id,
                    sequence=sequence - 1,
                    stop_type=stop_type,
                    status=view.status,
                    address=addr,
                    scheduled_at=view.scheduled_at,
                    tracking_number=view.tracking_number,
                    order_number=view.order_number,
                    special_instructions=view.special_instructions,
                    otp_required=view.otp_required,
                    pod_required=view.pod_required,
                )
            stops.append(view)
        return stops

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
        from porterchain_driver.job_legs import stop_status_for_leg

        addr = order.pickup if stop_type == "pickup" else order.dropoff
        state = str(order.state)
        return StopView(
            stop_id=f"{order.id}-{stop_type}",
            order_id=order.id,
            sequence=sequence,
            stop_type=stop_type,
            status=stop_status_for_leg(state, stop_type),
            address=addr or {},
            scheduled_at=order.scheduled_at,
            tracking_number=order.tracking_number,
            order_number=order.order_number or order.tracking_number,
            special_instructions=order.special_instructions,
            otp_required=stop_type == "dropoff",
            pod_required=stop_type == "dropoff",
        )
