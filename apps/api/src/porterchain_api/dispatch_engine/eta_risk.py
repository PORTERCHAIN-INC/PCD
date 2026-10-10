"""Live ETA and at-risk flags for in-flight orders.

ETA = now + Valhalla drive time from the driver's GPS last-known through the
remaining stops + learned time on site per stop (place → FSA → fleet default). Promise = ``sla_deadline_at``. An order is
``late`` past the promise, ``at_risk`` when ETA lands within ``at_risk_minutes``
of it (or beyond). No GPS or no Valhalla → ``unknown`` (never guessed).
"""

from __future__ import annotations

from porterchain_api.dispatch_engine.capabilities import order_needs_liftgate
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from porterchain_api.dispatch_engine.fleet_capacity import load_fleet
from porterchain_api.dispatch_engine.recommend import ACTIVE_STATES, Point, coords

BEFORE_PICKUP = {"DRIVER_ASSIGNED", "DRIVER_ACCEPTED", "DRIVER_EN_ROUTE", "AT_PICKUP"}
LIVE_CAP = 60


def classify(
    *, now: datetime, eta: datetime | None, promise: datetime | None, at_risk_minutes: int
) -> str:
    """on_time | at_risk | late | unknown — pure, unit-tested."""
    if promise is None:
        return "unknown"
    if promise.tzinfo is None:
        promise = promise.replace(tzinfo=timezone.utc)
    if now > promise:
        return "late"
    if eta is None:
        return "unknown"
    if eta >= promise - timedelta(minutes=at_risk_minutes):
        return "at_risk"
    return "on_time"


def remaining_points(order: Any, gps: Point | None) -> list[Point] | None:
    if gps is None:
        return None
    pickup, dropoff = coords(order.pickup), coords(order.dropoff)
    if dropoff is None:
        return None
    if order.state in BEFORE_PICKUP:
        return [gps, pickup, dropoff] if pickup else None
    return [gps, dropoff]


def eta_for(
    order: Any,
    gps: Point | None,
    *,
    now: datetime,
    service_fn: Callable[[str, Any], int],
    matrix_fn: Callable[[list[Point], str | None], "list[list[int]] | None"],
) -> datetime | None:
    """``service_fn(kind, address)`` → seconds on site at that remaining stop."""
    pts = remaining_points(order, gps)
    if not pts:
        return None
    matrix = matrix_fn(pts, None)
    if not matrix:
        return None
    seconds = sum(matrix[i][i + 1] for i in range(len(pts) - 1))
    kinds = ["pickup", "drop"] if len(pts) == 3 else ["drop"]
    addrs = {"pickup": order.pickup, "drop": order.dropoff}
    on_site = sum(service_fn(k, addrs[k]) for k in kinds)
    return now + timedelta(seconds=seconds + on_site)


def learned_service_fn(db: Any, default_s: int) -> Callable[[str, Any], int]:
    from porterchain_api.dispatch_engine import stop_times
    from porterchain_api.dispatch_engine.stop_shapes import fsa

    times = stop_times.load(db, default_s)

    def fn(kind: str, addr: Any) -> int:
        a = addr if isinstance(addr, dict) else {}
        pt = coords(a)
        return times.seconds(kind, fsa=fsa(a.get("postal") or a.get("postal_code")),
                             place=stop_times.place_key(*pt) if pt else None)

    return fn


def live_etas(
    db: Any,
    *,
    now: datetime | None = None,
    matrix_fn: Callable[[list[Point], str | None], "list[list[int]] | None"] | None = None,
    position_fn: Callable[[str], Point | None] | None = None,
) -> list[dict[str, Any]]:
    from porterchain_api.booking_models import Order
    from porterchain_api.dispatch_engine.recommend import _last_known, _valhalla

    now = now or datetime.now(timezone.utc)
    fleet = load_fleet(db)
    rows = (
        db.query(Order)
        .filter(Order.is_sandbox.is_(False), Order.state.in_(ACTIVE_STATES))
        .order_by(Order.sla_deadline_at.asc().nulls_last())
        .limit(LIVE_CAP)
        .all()
    )
    out = []
    pos = position_fn or _last_known
    fn = matrix_fn or _valhalla
    service_fn = learned_service_fn(db, int(float(fleet["service_minutes_per_stop"]) * 60))
    for o in rows:
        gps = pos(o.assigned_driver_id) if o.assigned_driver_id else None
        eta = eta_for(o, gps, now=now, service_fn=service_fn, matrix_fn=fn)
        status = classify(now=now, eta=eta, promise=o.sla_deadline_at, at_risk_minutes=int(fleet["at_risk_minutes"]))
        out.append(
            {
                "order_id": o.id,
                "order_number": o.order_number,
                "liftgate": order_needs_liftgate(o),
                "state": o.state,
                "driver_id": o.assigned_driver_id,
                "eta": eta.isoformat() if eta else None,
                "promise": o.sla_deadline_at.isoformat() if o.sla_deadline_at else None,
                "status": status,
                "has_gps": gps is not None,
            }
        )
    return out
