"""Applied day-plan waypoint sequence for a driver (interleaved PUDO).

PorterChain optimize/accept is the SoT. We cache the ordered pickup/dropoff legs
so ``StopsService`` and ``NextStopResolver`` can execute the tour without a
local TSP.

Version token + previous snapshot for admin/driver race + rollback;
idempotent apply by ``run_id``.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

CACHE_KEY = "porterchain:driver_sequence:{driver_id}"
CACHE_TTL_SECONDS = 12 * 60 * 60


class SequenceConflictError(Exception):
    """Admin vs driver reopt race — client must refresh and retry."""

    def __init__(self, *, current_version: int, expected_version: int | None) -> None:
        self.current_version = current_version
        self.expected_version = expected_version
        super().__init__(
            f"sequence_version_conflict:current={current_version}:expected={expected_version}"
        )


def cache_key(driver_id: str) -> str:
    return CACHE_KEY.format(driver_id=driver_id)


def read_sequence(driver_id: str) -> dict[str, Any] | None:
    try:
        from porterchain_shared.redis_client import get_redis_client

        raw = get_redis_client().get(cache_key(driver_id))
        if not raw:
            return None
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception as exc:  # noqa: BLE001 — miss is fine
        logger.debug("driver sequence read failed: %s", exc)
        return None


def write_sequence(driver_id: str, payload: dict[str, Any]) -> None:
    from porterchain_shared.redis_client import get_redis_client

    get_redis_client().setex(
        cache_key(driver_id),
        CACHE_TTL_SECONDS,
        json.dumps(payload),
    )


def _leg_type(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip().lower()
    if text in {"pickup", "pick_up", "pu", "collect"}:
        return "pickup"
    if text in {"dropoff", "drop_off", "delivery", "deliver", "do"}:
        return "dropoff"
    return None


def waypoints_from_assignments(assignments: list[Any]) -> list[dict[str, Any]]:
    """Flatten day-plan assignment rows into ordered pickup/dropoff waypoints."""
    rows = [a for a in assignments if isinstance(a, dict)]
    rows.sort(key=lambda a: int(a.get("sequence") or 0))
    waypoints: list[dict[str, Any]] = []
    seq = 0
    for row in rows:
        oid = row.get("porterchain_order_id") or row.get("order_id")
        if not oid:
            continue
        nested = row.get("stops") if isinstance(row.get("stops"), list) else []
        if nested:
            for stop in nested:
                if not isinstance(stop, dict):
                    continue
                leg = _leg_type(
                    stop.get("type")
                    or stop.get("stop_type")
                    or stop.get("kind")
                    or stop.get("task")
                )
                if not leg:
                    continue
                waypoints.append(
                    {
                        "sequence": seq,
                        "order_id": str(oid),
                        "stop_type": leg,
                        "vehicle_id": row.get("vehicle_id"),
                        "driver_id": row.get("driver_id"),
                    }
                )
                seq += 1
            continue
        # Order-level assignment: preserve tour order as pickup then dropoff
        # for that order (a later reopt may re-interleave).
        for leg in ("pickup", "dropoff"):
            waypoints.append(
                {
                    "sequence": seq,
                    "order_id": str(oid),
                    "stop_type": leg,
                    "vehicle_id": row.get("vehicle_id"),
                    "driver_id": row.get("driver_id"),
                }
            )
            seq += 1
    return waypoints


def apply_run_to_driver(
    driver_id: str,
    rec: dict[str, Any],
    *,
    expected_version: int | None = None,
) -> list[dict[str, Any]]:
    """Persist waypoints from a ready optimize run. Returns waypoints written.

    Idempotent on ``run_id``. Raises ``SequenceConflictError`` when
    ``expected_version`` does not match the live sequence version (409 path).
    """
    if (rec.get("status") or "") != "ready":
        return []
    run_id = str(rec.get("run_id") or "").strip()
    prev = read_sequence(driver_id)
    current_version = int((prev or {}).get("version") or 0)

    if expected_version is not None and int(expected_version) != current_version:
        raise SequenceConflictError(
            current_version=current_version, expected_version=int(expected_version)
        )

    # Idempotent: same run already applied — no-op (webhook/retry safe).
    if run_id and prev and str(prev.get("run_id") or "") == run_id:
        return list(prev.get("waypoints") or [])

    waypoints = waypoints_from_assignments(list(rec.get("assignments") or []))
    if not waypoints:
        return []
    metrics = rec.get("metrics") if isinstance(rec.get("metrics"), dict) else {}
    # Keep prior plan for undo (strip nested previous to bound Redis size).
    previous_snapshot = None
    if prev:
        previous_snapshot = {
            k: prev[k]
            for k in ("run_id", "engine", "waypoints", "metrics", "version", "source")
            if k in prev
        }

    payload = {
        "run_id": run_id or None,
        "engine": rec.get("engine") or metrics.get("engine"),
        "waypoints": waypoints,
        "metrics": {
            k: metrics[k]
            for k in (
                "after_distance_km",
                "after_duration_min",
                "estimated_fuel_cents",
                "estimated_fuel_liters",
                "fuel_delta_cents",
                "distance_delta_km",
                "valhalla_costing",
            )
            if k in metrics
        },
        "source": "fleetbase_optimize",
        "version": current_version + 1,
        "previous": previous_snapshot,
    }
    write_sequence(driver_id, payload)
    return waypoints


def rollback_sequence(driver_id: str) -> dict[str, Any] | None:
    """Restore previous sequence snapshot (undo optimize). Returns restored plan."""
    current = read_sequence(driver_id)
    if not current:
        return None
    previous = current.get("previous")
    if not isinstance(previous, dict) or not previous.get("waypoints"):
        return None
    restored = {
        **previous,
        "version": int(current.get("version") or 0) + 1,
        "previous": {
            k: current[k]
            for k in ("run_id", "engine", "waypoints", "metrics", "version", "source")
            if k in current
        },
        "source": "rollback",
    }
    write_sequence(driver_id, restored)
    try:
        from porterchain_api.dispatch_engine.optimize_events import emit_rolled_back

        emit_rolled_back(
            str(current.get("run_id") or "unknown"),
            pc_driver_id=driver_id,
            restored_run_id=restored.get("run_id"),
            version=restored.get("version"),
        )
    except Exception:  # noqa: BLE001
        pass
    return restored
