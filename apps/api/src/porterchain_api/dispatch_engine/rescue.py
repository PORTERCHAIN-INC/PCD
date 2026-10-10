"""Vehicle breakdown → one-action rescue (van-to-van transfer).

``rescue`` does the whole thing an admin approves in Exceptions:

1. picks the rescue vehicle: the nearest online approved driver whose vehicle can carry
   everything still on the broken van (or the one the admin named);
2. sets the meet point at the broken van's last GPS fix;
3. moves every open order to the rescue driver and edits the committed plan: a handover
   stop at the meet point per order, then the orders' remaining stops, ahead of the
   rescue driver's own pending work;
4. resets the carried boxes to "manifested" so the rescue driver must scan each one over
   (the normal scan-gated pickup at the meet point);
5. emails a customer (``order.delayed``) only when the new arrival is more than
   ``SLIP_ALERT_S`` later than the broken van would have made it.

Road times come from Valhalla (free, self-hosted); nothing here guesses when the router is down.
Engine-neutral: the caller injects road times, GPS, candidate vehicles and the delay email.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

ACTIVE = ("DRIVER_ASSIGNED", "DRIVER_ACCEPTED", "DRIVER_EN_ROUTE", "AT_PICKUP", "PICKED_UP", "IN_TRANSIT",
          "AT_DESTINATION")
ONBOARD = {"PICKED_UP", "IN_TRANSIT", "AT_DESTINATION"}
HANDOVER_S = 600  # park, open both vans, scan every box across
SLIP_ALERT_S = 15 * 60
# Package statuses (scan gate vocabulary): carried boxes go back to "manifested" for the handover scan.
MANIFESTED, DELIVERED, MISSING_AT_PICKUP = "manifested", "delivered", "missing_at_pickup"
Matrix = Callable[[list[tuple[float, float]]], list[list[int]] | None]
Position = Callable[[str], tuple[float, float] | None]
Vehicles = Callable[[Session, list[str] | None], list[Any]]  # -> vrp.Vehicle rows (online, capacity, start)
EmailDelay = Callable[[Session, Any, Any, str], None]  # (db, ctx, order, message)


def _drop_point(order: Any) -> tuple[float, float] | None:
    side = order.dropoff if isinstance(order.dropoff, dict) else {}
    first = (side.get("stops") or [side])[0] if isinstance(side.get("stops"), list) else side
    lat, lng = first.get("lat"), first.get("lng")
    return (float(lat), float(lng)) if lat is not None and lng is not None else None


class RescueService:
    def __init__(self, *, matrix_fn: Matrix, position_fn: Position, vehicles_fn: Vehicles,
                 email_delay: EmailDelay) -> None:
        self.matrix_fn, self.position_fn = matrix_fn, position_fn
        self.vehicles_fn, self.email_delay = vehicles_fn, email_delay

    def rescue(self, db: Session, ctx: Any, *, broken_driver_id: str, rescue_driver_id: str | None = None,
               now: datetime | None = None) -> dict[str, Any]:
        from porterchain_api.admin_models import Driver
        from porterchain_api.booking_models import Order, OrderException
        from porterchain_api.dispatch_engine.fleet_capacity import order_load

        now = now or datetime.now(UTC)
        orders = (db.query(Order).filter(Order.assigned_driver_id == broken_driver_id, Order.state.in_(ACTIVE))
                  .order_by(Order.created_at).all())
        if not orders:
            raise LookupError("nothing_to_rescue")
        meet = self.position_fn(broken_driver_id)
        if meet is None:
            raise ValueError("broken_van_position_unknown")
        broken = db.get(Driver, broken_driver_id)

        onboard = [o for o in orders if o.state in ONBOARD]
        boxes = sum(order_load(o).boxes for o in onboard)
        kg = sum(order_load(o).kg for o in onboard)
        only = [rescue_driver_id] if rescue_driver_id else None
        candidates = [v for v in self.vehicles_fn(db, only)
                      if v.driver_id != broken_driver_id and v.cap_boxes >= boxes and v.cap_kg >= kg
                      and self.position_fn(v.driver_id) is not None]  # no GPS fix → can't promise a meet time
        if not candidates:
            raise ValueError("no_rescue_vehicle_fits")
        drops = [_drop_point(o) for o in orders]
        pts = [meet] + [v.start for v in candidates] + [d or meet for d in drops]
        matrix = self.matrix_fn(pts)
        if matrix is None:
            raise ValueError("road_router_unavailable")
        n = len(candidates)
        best_i = min(range(n), key=lambda i: matrix[1 + i][0])
        rescuer = candidates[best_i]
        to_meet = matrix[1 + best_i][0]

        # ---- plan: move stops to the rescue route, handover first
        moved_keys = self._move_stops(db, orders, broken_driver_id, rescuer.driver_id, meet, broken)

        # ---- orders, boxes, customer emails
        notified, etas = [], {}
        for k, o in enumerate(orders):
            o.assigned_driver_id = rescuer.driver_id
            if o.state in ONBOARD:
                for p in o.packages:
                    if p.status not in (DELIVERED, MISSING_AT_PICKUP):
                        p.status = MANIFESTED  # rescue driver scans it over at the meet point
            drop_cell = 1 + n + k
            if drops[k] is None:
                continue
            before = matrix[0][drop_cell]  # broken van would have driven from where it stopped
            after = to_meet + HANDOVER_S + matrix[0][drop_cell]
            slip = after - before
            etas[o.id] = {"eta": (now + timedelta(seconds=after)).isoformat(), "slip_min": round(slip / 60)}
            if o.state in ONBOARD and slip > SLIP_ALERT_S:
                local = (now + timedelta(seconds=after)).astimezone(ZoneInfo("America/Toronto"))
                self.email_delay(db, ctx, o, f"Your delivery moved to another van. New arrival around {local:%-I:%M %p}.")
                notified.append(o.id)
        for exc in db.query(OrderException).filter(OrderException.order_id.in_([o.id for o in orders]),
                                                   OrderException.type == "VEHICLE_BREAKDOWN",
                                                   OrderException.status.in_(("open", "acknowledged"))):
            exc.status, exc.resolved_at = "resolved", now
            exc.resolution = {"action": "rescue", "rescue_driver_id": rescuer.driver_id}
        if broken is not None:
            broken.is_online = False  # off the planner until the van is fixed
        db.commit()
        return {"rescue_driver_id": rescuer.driver_id, "meet": {"lat": meet[0], "lng": meet[1]},
                "meet_eta_min": round(to_meet / 60), "orders": [o.id for o in orders],
                "boxes_to_scan": boxes, "stops_moved": len(moved_keys), "etas": etas, "emailed": notified}

    # ------------------------------------------------------------------ plan edit
    @staticmethod
    def _move_stops(db: Session, orders: list[Any], broken_id: str, rescue_id: str, meet: tuple[float, float],
                    broken: Any) -> list[str]:
        from porterchain_api.dispatch_engine.driver_route import DriverRouteService
        from porterchain_api.dispatch_engine.models import DispatchRoute

        routes = DriverRouteService()
        src = routes.current_route(db, broken_id)
        dst = routes.current_route(db, rescue_id)
        ids = {o.id for o in orders}
        done = routes.done_keys(db, [r.id for r in (src, dst) if r is not None])
        moving = [s for s in (src.stops if src else []) if s["order_id"] in ids and s["key"] not in done]
        if src is not None:
            src.stops = [s for s in src.stops if s not in moving]
        if dst is None:
            if src is None:
                return []
            dst = DispatchRoute(plan_id=src.plan_id, vehicle_id=f"v-{rescue_id}", driver_id=rescue_id,
                                vehicle_class=src.vehicle_class, stops=[], status=src.status)
            db.add(dst)
        name = (getattr(broken, "full_name", None) or "the broken van").split(" ")[0]
        handover = [{
            "key": f"{o.id}:m0:rescue", "order_id": o.id, "kind": "pickup", "eta_s": 0,
            "meet": {"lat": meet[0], "lng": meet[1], "formatted": f"Rescue handover · meet {name}'s van"},
        } for o in orders if o.state in ONBOARD]
        kept_done = [s for s in dst.stops if s["key"] in done]
        pending = [s for s in dst.stops if s["key"] not in done]
        dst.stops = kept_done + handover + moving + pending
        db.flush()
        return [s["key"] for s in handover + moving]
