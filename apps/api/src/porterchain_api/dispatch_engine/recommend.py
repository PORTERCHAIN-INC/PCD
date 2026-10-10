"""Driver + vehicle recommendation for one order (rules-first, free stack).

1. Vehicle: smallest enabled vehicle class keeping fill ≤ max_fill (85%).
2. Drivers: approved, verified, online or on an open shift, owning an active
   vehicle that can carry their current load plus this order at ≤ max_fill.
3. Insertion cost: Valhalla drive minutes from the driver's start point (GPS
   last-known when idle, last committed drop-off when busy) to pickup, then to
   drop-off, plus service minutes per stop. Valhalla only — no straight-line
   fallback; without a Valhalla matrix candidates are returned unranked by time.
4. Cost: the settings-driven driver pay plan for that time and 1 pickup + 1 stop.
   Lowest cost wins; ties go to the smaller vehicle, then fewer active jobs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from porterchain_api.dispatch_engine.fleet_capacity import (
    RANK,
    Load,
    canonical_class,
    fill_ratio,
    ft3,
    load_fleet,
    order_load,
    smallest_fitting,
    vehicle_by_id,
)

ACTIVE_STATES = (
    "DRIVER_ASSIGNED",
    "DRIVER_ACCEPTED",
    "DRIVER_EN_ROUTE",
    "AT_PICKUP",
    "PICKED_UP",
    "IN_TRANSIT",
    "AT_DESTINATION",
)
CANDIDATE_CAP = 40  # Valhalla matrix stays small; online drivers ranked first

Point = tuple[float, float]
MatrixFn = Callable[[list[Point], str | None], "list[list[int]] | None"]


def coords(addr: Any) -> Point | None:
    if not isinstance(addr, dict):
        return None
    lat = addr.get("lat", addr.get("latitude"))
    lng = addr.get("lng", addr.get("lon", addr.get("longitude")))
    try:
        if lat is None or lng is None:
            return None
        return float(lat), float(lng)
    except (TypeError, ValueError):
        return None


@dataclass
class Candidate:
    driver_id: str
    name: str
    vehicle_class: str | None
    active_jobs: int
    current_load: Load
    start: Point | None
    start_source: str
    fill_after: float | None = None
    minutes: float | None = None
    cost_cents: int | None = None
    reasons: list[str] = field(default_factory=list)
    blocked: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "driver_id": self.driver_id,
            "name": self.name,
            "vehicle_class": self.vehicle_class,
            "active_jobs": self.active_jobs,
            "fill_after_pct": None if self.fill_after is None else round(self.fill_after * 100, 1),
            "insertion_minutes": None if self.minutes is None else round(self.minutes, 1),
            "cost_cents": self.cost_cents,
            "start_source": self.start_source,
            "reasons": self.reasons,
            "blocked": self.blocked,
        }


def pay_cents(plan_raw: Any, minutes: float, *, hourly_fallback_cents: int) -> int:
    """Driver-pay-plan cost of one pickup + one stop taking ``minutes``."""
    try:
        from porterchain_pricing.driver_pay import compute_driver_pay

        return int(compute_driver_pay(plan_raw, paid_minutes=minutes, stops=1, pickups=1).total_cents)
    except (ImportError, ValueError):
        return int(round(minutes / 60.0 * hourly_fallback_cents))


def rank(candidates: list[Candidate]) -> list[Candidate]:
    """Feasible first; then cost, smaller vehicle, fewer active jobs, minutes."""

    def key(c: Candidate) -> tuple:
        return (
            c.blocked is not None,
            c.cost_cents if c.cost_cents is not None else 10**9,
            RANK.get(c.vehicle_class or "", 9),
            c.active_jobs,
            c.minutes if c.minutes is not None else 10**6,
        )

    return sorted(candidates, key=key)


def score_insertion(
    candidates: list[Candidate],
    pickup: Point,
    dropoff: Point,
    *,
    matrix: list[list[int]] | None,
    service_minutes: float,
    plan_raw: Any,
    hourly_cents: int,
) -> None:
    """Fill minutes/cost in place. ``matrix`` rows/cols: starts…, pickup, dropoff."""
    n = len(candidates)
    pu, do = n, n + 1
    for i, cand in enumerate(candidates):
        if cand.blocked:
            continue
        if matrix is None or cand.start is None:
            cand.reasons.append("no Valhalla time" if matrix is None else "no position")
            continue
        seconds = matrix[i][pu] + matrix[pu][do]
        cand.minutes = seconds / 60.0 + 2 * service_minutes
        cand.cost_cents = pay_cents(plan_raw, cand.minutes, hourly_fallback_cents=hourly_cents)
        cand.reasons.append(f"{round(matrix[i][pu] / 60)} min to pickup")


def _valhalla(points: list[Point], vehicle_class: str | None) -> list[list[int]] | None:
    from porterchain_api.dispatch_engine.day_plan import drive_seconds

    try:
        matrix, _ = drive_seconds(points, vehicle_class=vehicle_class)
    except Exception:  # noqa: BLE001 — Valhalla down must not break the board
        return None
    return matrix


def _last_known(driver_id: str) -> Point | None:
    try:
        from porterchain_api.platform.last_known import read_last_known

        lk = read_last_known(driver_id)
    except Exception:  # noqa: BLE001
        return None
    return (lk.lat, lk.lng) if lk else None


def recommend_for_order(
    db: Any,
    order_id: str,
    *,
    matrix_fn: MatrixFn | None = None,
    position_fn: Callable[[str], Point | None] | None = None,
    gap_fn: Callable[[Any], str | None] | None = None,
    driver_ids: list[str] | None = None,
) -> dict[str, Any]:
    """``gap_fn`` is the admin verification gate (licence/insurance/background);
    injected by the admin layer so dispatch_engine does not import admin_engine."""
    from porterchain_api.admin_models import Driver, SystemConfig, Vehicle
    from porterchain_api.booking_models import Order
    from porterchain_api.domain.admin_states import DriverStatus
    from porterchain_api.driver_models import DriverShift

    order = db.get(Order, order_id)
    if order is None:
        raise LookupError("order_not_found")
    fleet = load_fleet(db)
    plan_row = db.get(SystemConfig, "driver_pay_plan")
    plan_raw = plan_row.value if plan_row is not None else None
    load = order_load(order)
    vehicle = smallest_fitting(load, fleet)
    pickup, dropoff = coords(order.pickup), coords(order.dropoff)

    open_shift_ids = {
        r[0] for r in db.query(DriverShift.driver_id).filter(DriverShift.ended_at.is_(None)).all()
    }
    q = db.query(Driver).filter(Driver.status == DriverStatus.APPROVED.value)
    if driver_ids:
        q = q.filter(Driver.id.in_(driver_ids))
    drivers = q.order_by(Driver.is_online.desc(), Driver.updated_at.desc()).limit(500).all()
    pool = [d for d in drivers if d.is_online or d.availability == "online" or d.id in open_shift_ids]

    cands: list[Candidate] = []
    pos = position_fn or _last_known
    for d in pool[:CANDIDATE_CAP]:
        active = (
            db.query(Order)
            .filter(Order.assigned_driver_id == d.id, Order.state.in_(ACTIVE_STATES), Order.id != order.id)
            .order_by(Order.scheduled_at)
            .all()
        )
        current = Load()
        for o in active:
            current = current + order_load(o)
        vehicles = (
            db.query(Vehicle).filter(Vehicle.driver_id == d.id, Vehicle.is_active.is_(True)).all()
        )
        classes = sorted(
            {c for c in (canonical_class(v.vehicle_class) for v in vehicles) if c},
            key=lambda c: RANK.get(c, 9),
        )
        start, source = (coords(active[-1].dropoff), "last drop-off") if active else (pos(d.id), "GPS")
        cand = Candidate(d.id, d.full_name, classes[0] if classes else None, len(active), current, start, source)
        gap = gap_fn(d) if gap_fn else None
        if gap:
            cand.blocked = gap
        elif not classes:
            cand.blocked = "no_active_vehicle"
        else:
            total = current + load
            fits = [c for c in classes if (vb := vehicle_by_id(fleet, c)) and fill_ratio(total, vb) <= fleet["max_fill"]]
            if not fits:
                cand.blocked = "over_capacity"
                vb = vehicle_by_id(fleet, classes[-1])
                cand.fill_after = fill_ratio(total, vb) if vb else None
            else:
                cand.vehicle_class = fits[0]
                vb = vehicle_by_id(fleet, fits[0])
                cand.fill_after = fill_ratio(total, vb) if vb else None
        cands.append(cand)

    matrix = None
    if pickup and dropoff and any(c.start and not c.blocked for c in cands):
        live = [c for c in cands if not c.blocked and c.start]
        points = [c.start for c in live] + [pickup, dropoff]  # type: ignore[misc]
        fn = matrix_fn or _valhalla
        matrix = fn(points, vehicle["id"] if vehicle else None)
        score_insertion(
            live, pickup, dropoff, matrix=matrix,
            service_minutes=float(fleet["service_minutes_per_stop"]),
            plan_raw=plan_raw, hourly_cents=int(fleet["hourly_cost_cents"]),
        )
    ranked = rank(cands)
    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "load": {"kg": load.kg, "m3": load.m3, "ft3": ft3(load.m3), "boxes": load.boxes},
        "vehicle": None
        if vehicle is None
        else {
            "id": vehicle["id"],
            "label": vehicle["label"],
            "fill_pct": round(fill_ratio(load, vehicle) * 100, 1),
        },
        "vehicle_reason": "smallest vehicle at or under "
        f"{int(fleet['max_fill'] * 100)}% full" if vehicle else "no enabled vehicle fits — split the load or subcontract",
        "matrix": "valhalla" if matrix is not None else "unavailable",
        "drivers": [c.as_dict() for c in ranked],
        "best_driver_id": next((c.driver_id for c in ranked if not c.blocked), None),
        "hourly_cost_cents": fleet["hourly_cost_cents"],
    }
