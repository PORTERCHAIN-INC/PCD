"""Driver stop-order helpers. One van is sequenced by the PorterChain worker."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from porterchain_api.order_engine.buckets import DELIVERY_ONLY_POOL, HIGH_PRIORITY_CENTS

_COMPLETED = frozenset(
    {
        "DELIVERED",
        "POD_COMPLETED",
        "INVOICED",
        "CLOSED",
        "CANCELLED",
        "FAILED",
        "RETURN_TO_SENDER",
        "DAMAGED",
        "LOST",
        "REFUNDED",
    }
)


def _coords(addr: dict | None) -> tuple[float, float] | None:
    if not addr:
        return None
    lat = addr.get("lat") or addr.get("latitude")
    lng = addr.get("lng") or addr.get("lon") or addr.get("longitude")
    if lat is None or lng is None:
        return None
    return float(lat), float(lng)


def compute_urgency(order: Any, *, now: datetime | None = None) -> str:
    """critical > high > medium > normal based on SLA window and order value."""
    now = now or datetime.now(UTC)
    high_value = (order.amount_cents or 0) >= HIGH_PRIORITY_CENTS
    scheduled = order.scheduled_at
    if scheduled is not None:
        if scheduled.tzinfo is None:
            scheduled = scheduled.replace(tzinfo=UTC)
        hours = (scheduled - now).total_seconds() / 3600
        if hours < 0:
            return "critical"
        if hours <= 1:
            return "critical" if high_value else "high"
        if hours <= 3:
            return "high" if high_value else "medium"
        if hours <= 6 and high_value:
            return "high"
    return "high" if high_value else "normal"


class DriverRouteOptimizer:
    """Stop-count / urgency helpers. The worker sequences one van."""

    def can_optimize(self, active_orders: list[Any]) -> bool:
        stop_count = 0
        for order in active_orders:
            delivery_only = str(order.state) in DELIVERY_ONLY_POOL
            pickup = order.pickup or {}
            dropoff = order.dropoff or {}
            pickup_coords = _coords(pickup)
            dropoff_coords = _coords(dropoff)
            if delivery_only:
                if dropoff_coords:
                    stop_count += 1
            else:
                if pickup_coords:
                    stop_count += 1
                if dropoff_coords:
                    stop_count += 1
        return stop_count >= 2

    def priority_ranks_from_plan(self, plan: Any | None) -> dict[str, int]:
        if not plan or not getattr(plan, "stops", None):
            return {}
        ranks: dict[str, int] = {}
        rank = 0
        for stop in sorted(plan.stops, key=lambda s: int(s.get("sequence") or 0)):
            oid = stop.get("order_id")
            if oid and oid not in ranks:
                rank += 1
                ranks[oid] = rank
        return ranks

    def reoptimize_remaining(self, db: Any, driver: Any, completed_stop_id: str) -> dict[str, Any] | None:
        """After a stop completes, queue one van for the worker. A break skips the search."""
        from porterchain_driver.stops import StopsService

        del completed_stop_id  # remaining set is derived from live order states

        if driver is None or db is None:
            return None

        if str(getattr(driver, "availability", "") or "") == "on_break":
            return None

        orders = [
            o
            for o in StopsService()._today_orders(db, driver.id)  # noqa: SLF001
            if str(o.state) not in _COMPLETED
        ]
        if not self.can_optimize(orders):
            return None

        ordered = _soft_order(driver, orders)
        vehicle_class = _vehicle_class(db, driver.id)
        from porterchain_api.dispatch_engine.day_plan import payload_from_orders, queue_one_van

        payload = payload_from_orders(
            ordered,
            vehicle_class=vehicle_class,
            driver_id=str(driver.id),
            origin=_origin(driver),
        )
        rec = queue_one_van(payload)
        if rec.get("error"):
            return None
        return {
            "run_id": rec.get("run_id"),
            "status": rec.get("status"),
            "mode": "optimize_routes",
            "engine": "porterchain",
            "order_count": len(ordered),
            "order_ids": [str(o.id) for o in ordered],
            "soft_sequence": True,
        }


def _soft_order(driver: Any, orders: list[Any]) -> list[Any]:
    by_id = {str(order.id): order for order in orders}
    ordered: list[Any] = []
    seen: set[str] = set()
    try:
        from porterchain_driver.sequence_store import read_sequence

        plan = read_sequence(str(driver.id))
        if isinstance(plan, dict):
            for wp in plan.get("waypoints") or []:
                if not isinstance(wp, dict):
                    continue
                oid = str(wp.get("order_id") or "")
                if oid in by_id and oid not in seen:
                    ordered.append(by_id[oid])
                    seen.add(oid)
    except Exception:  # noqa: BLE001 — a missing sequence still plans the live jobs
        return list(orders)
    for order in orders:
        if str(order.id) not in seen:
            ordered.append(order)
    return ordered


def _vehicle_class(db: Any, driver_id: Any) -> str | None:
    try:
        from porterchain_api.admin_models import Vehicle

        vehicles = (
            db.query(Vehicle)
            .filter(Vehicle.driver_id == driver_id, Vehicle.is_active.is_(True))
            .all()
        )
    except Exception:  # noqa: BLE001
        return None
    for vehicle in vehicles:
        kind = getattr(vehicle, "vehicle_class", None)
        if kind:
            return str(kind)
    return None


def _origin(driver: Any) -> dict[str, float] | None:
    lat = getattr(driver, "last_lat", None)
    lng = getattr(driver, "last_lng", None)
    if lat is None or lng is None:
        return None
    return {"lat": float(lat), "lng": float(lng)}
