"""Driver stop-order helpers — Fleetbase owns sequencing.

Do not solve TSP/VRP here. Preview is enqueue → Fleetbase orchestrator.
Post-pickup reopt uses Fleetbase ``optimize_routes`` + ``prior_assignments``.
"""

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
    """Stop-count / urgency helpers. Sequencing is Fleetbase orchestrator only."""

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
        """After a stop completes (or fails), re-sequence remaining jobs via Fleetbase.

        Uses ``mode=optimize_routes`` + ``engine=vroom``, locked to this driver's
        vehicle, with ``prior_assignments`` so already-assigned (incl. PICKED_UP)
        orders stay on that vehicle. Soft consistency: prefer existing sequence
        order when present (Phase 6). Never runs a local TSP. Skips while driver
        is on break (HOS — break windows not yet fed into Fleetbase VROOM).
        """
        from porterchain_api.admin_engine.orchestrator_ops_service import OrchestratorOpsService
        from porterchain_api.admin_models import Vehicle
        from porterchain_api.fleetbase_engine.public_ids import is_consumable_public_id
        from porterchain_driver.stops import StopsService

        del completed_stop_id  # remaining set is derived from live order states

        if driver is None or db is None:
            return None

        # Phase 6 HOS: do not reshuffle while on break — shift break is SoT until
        # Fleetbase OrderConfig exposes break windows we can feed to VROOM.
        if str(getattr(driver, "availability", "") or "") == "on_break":
            return None

        orders = [
            o
            for o in StopsService()._today_orders(db, driver.id)  # noqa: SLF001
            if str(o.state) not in _COMPLETED
        ]
        if not self.can_optimize(orders):
            return None

        synced = [
            o for o in orders if is_consumable_public_id(getattr(o, "fleetbase_order_id", None))
        ]
        if len(synced) < 1:
            return None

        vehicles = (
            db.query(Vehicle)
            .filter(
                Vehicle.driver_id == driver.id,
                Vehicle.is_active.is_(True),
                Vehicle.fleetbase_vehicle_id.isnot(None),
            )
            .all()
        )
        vehicle_ids = [
            v.fleetbase_vehicle_id
            for v in vehicles
            if is_consumable_public_id(v.fleetbase_vehicle_id)
        ]
        fb_driver = getattr(driver, "fleetbase_driver_id", None)
        driver_ids = [fb_driver] if is_consumable_public_id(fb_driver) else []
        if not vehicle_ids:
            return None

        primary_vehicle = vehicle_ids[0]
        # Soft day-to-day consistency: keep prior vehicle lock order aligned with
        # the last applied Fleetbase sequence when available.
        synced_by_id = {str(o.id): o for o in synced}
        fb_by_pc = {
            str(o.id): o.fleetbase_order_id
            for o in synced
            if o.fleetbase_order_id
        }
        ordered: list[Any] = []
        try:
            from porterchain_driver.sequence_store import read_sequence

            plan = read_sequence(str(driver.id))
            seen: set[str] = set()
            if isinstance(plan, dict):
                for wp in plan.get("waypoints") or []:
                    if not isinstance(wp, dict):
                        continue
                    oid = str(wp.get("order_id") or "")
                    if oid in synced_by_id and oid not in seen:
                        ordered.append(synced_by_id[oid])
                        seen.add(oid)
            for o in synced:
                if str(o.id) not in seen:
                    ordered.append(o)
        except Exception:  # noqa: BLE001
            ordered = list(synced)

        prior_assignments = [
            {
                "order_id": o.fleetbase_order_id,
                "vehicle_id": primary_vehicle,
                "driver_id": fb_driver if driver_ids else None,
            }
            for o in ordered
            if o.fleetbase_order_id
        ]
        del fb_by_pc

        rec = OrchestratorOpsService().enqueue_run(
            db,
            order_ids=[o.id for o in ordered],
            mode="optimize_routes",
            engine="vroom",
            shape="vehicle",
            vehicle_ids=vehicle_ids,
            driver_ids=driver_ids or None,
            prior_assignments=prior_assignments,
            pc_driver_id=driver.id,
        )
        if rec.get("error"):
            return None
        return {
            "run_id": rec.get("run_id"),
            "status": rec.get("status"),
            "mode": "optimize_routes",
            "engine": "vroom",
            "order_count": len(ordered),
            "vehicle_ids": vehicle_ids,
            "prior_assignments": prior_assignments,
            "soft_sequence": True,
        }
