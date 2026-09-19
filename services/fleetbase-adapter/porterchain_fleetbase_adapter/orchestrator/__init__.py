"""Fleetbase Orchestrator — run/commit via public API (fleetops-api 0.6.59).

Creates vehicle manifests on commit. Does not replace Fleetbase workbench;
PorterChain only wraps the consumable endpoints for Control Tower Optimize.
"""

from __future__ import annotations

import logging
from typing import Any

from porterchain_fleetbase_adapter.client import FleetbaseClient
from porterchain_fleetbase_adapter.config import FleetbaseSettings
from porterchain_fleetbase_adapter.errors import ErrorHandler

logger = logging.getLogger(__name__)

RUN_PATH = "/v1/orchestrator/run"
COMMIT_PATH = "/v1/orchestrator/commit"
# Engines listing is internal-only upstream; try then degrade.
ENGINES_PATH = "/int/v1/fleet-ops/orchestrator/engines"


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def normalize_run_result(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Flatten engine result into PC Optimize metrics + assignment rows."""
    body = _as_dict(raw)
    if "error" in body and not body.get("assignments"):
        return {
            "ok": False,
            "error": body.get("error"),
            "hint": body.get("hint"),
            "engine": body.get("engine"),
            "assignments": [],
            "unassigned": _as_list(body.get("unassigned")),
            "unassigned_details": _normalize_unassigned_details(body),
            "metrics": {},
            "raw": body,
        }

    assignments = _as_list(body.get("assignments"))
    unassigned = _as_list(body.get("unassigned"))
    # Some engines nest under plan/result
    if not assignments and isinstance(body.get("plan"), dict):
        plan = body["plan"]
        assignments = _as_list(plan.get("assignments"))
        unassigned = _as_list(plan.get("unassigned")) or unassigned

    rows: list[dict[str, Any]] = []
    total_distance = 0
    total_duration = 0
    vehicles: set[str] = set()
    for a in assignments:
        if not isinstance(a, dict):
            continue
        dist = a.get("distance") or a.get("distance_m") or a.get("total_distance_m") or 0
        dur = a.get("duration") or a.get("duration_s") or a.get("total_duration_s") or 0
        try:
            dist_i = int(float(dist))
            dur_i = int(float(dur))
        except (TypeError, ValueError):
            dist_i, dur_i = 0, 0
        total_distance += dist_i
        total_duration += dur_i
        vehicle_id = a.get("vehicle_id") or a.get("vehicle_public_id")
        if vehicle_id:
            vehicles.add(str(vehicle_id))
        rows.append(
            {
                "order_id": a.get("order_id") or a.get("order_public_id"),
                "vehicle_id": vehicle_id,
                "driver_id": a.get("driver_id") or a.get("driver_public_id"),
                "distance_m": dist_i,
                "duration_s": dur_i,
                "sequence": a.get("sequence"),
                "stops": a.get("stops") if isinstance(a.get("stops"), list) else [],
            }
        )

    assigned = len(rows)
    details = _normalize_unassigned_details(body, unassigned)
    unassigned_ids = [d["order_id"] for d in details if d.get("order_id")]
    # Keep string-only unassigned ids for backward-compatible consumers.
    if not unassigned_ids:
        unassigned_ids = [u if isinstance(u, str) else _as_dict(u).get("order_id") for u in unassigned]
        unassigned_ids = [u for u in unassigned_ids if u]
    vehicle_count = len(vehicles) or 1
    utilization = round(assigned / vehicle_count, 2) if assigned else 0.0
    capacity_rejects = [
        d for d in details if _is_capacity_reject_reason(str(d.get("reason") or ""))
    ]

    return {
        "ok": True,
        "message": body.get("message"),
        "assignments": rows,
        "unassigned": unassigned_ids,
        "unassigned_details": details,
        "metrics": {
            "assigned_count": assigned,
            "unassigned_count": len(unassigned_ids),
            "capacity_reject_count": len(capacity_rejects),
            "vehicles_used": len(vehicles),
            "after_distance_m": total_distance,
            "after_duration_s": total_duration,
            "after_distance_km": round(total_distance / 1000, 2) if total_distance else 0.0,
            "after_duration_min": round(total_duration / 60, 1) if total_duration else 0.0,
            "utilization_orders_per_vehicle": utilization,
        },
        "raw": body,
    }


def _is_capacity_reject_reason(reason: str) -> bool:
    r = reason.lower()
    return any(
        token in r
        for token in (
            "capacity",
            "no_available_vehicle",
            "too heavy",
            "too_large",
            "payload",
            "volume",
            "dimension",
        )
    )


def _normalize_unassigned_details(
    body: dict[str, Any], unassigned: list[Any] | None = None
) -> list[dict[str, Any]]:
    """Preserve Fleetbase unassigned reasons (capacity rejects, invalid coords, …)."""
    raw_list = _as_list(unassigned if unassigned is not None else body.get("unassigned"))
    reasons = _as_list(body.get("unassigned_reasons") or _as_dict(body.get("summary")).get("unassigned_reasons"))
    reason_by_id: dict[str, str] = {}
    for row in reasons:
        if not isinstance(row, dict):
            continue
        oid = row.get("id") or row.get("order_id") or row.get("job_id")
        if oid:
            reason_by_id[str(oid)] = str(row.get("reason") or row.get("code") or "unassigned")

    details: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw_list:
        if isinstance(item, str):
            oid = item
            reason = reason_by_id.get(oid) or "unassigned"
            row = {"order_id": oid, "reason": reason}
        else:
            d = _as_dict(item)
            oid = d.get("order_id") or d.get("id") or d.get("job_id")
            if not oid:
                continue
            oid = str(oid)
            reason = str(d.get("reason") or d.get("code") or reason_by_id.get(oid) or "unassigned")
            row = {"order_id": oid, "reason": reason}
            if d.get("hint"):
                row["hint"] = d["hint"]
        if oid in seen:
            continue
        seen.add(str(oid))
        details.append(row)
    for oid, reason in reason_by_id.items():
        if oid not in seen:
            details.append({"order_id": oid, "reason": reason})
            seen.add(oid)
    return details


def normalize_commit_result(raw: dict[str, Any] | None) -> dict[str, Any]:
    body = _as_dict(raw)
    manifests = _as_list(body.get("manifests"))
    return {
        "ok": "error" not in body,
        "error": body.get("error"),
        "committed": _as_list(body.get("committed")),
        "failed": _as_list(body.get("failed")),
        "manifests": manifests,
        "manifest_count": len(manifests),
        "raw": body,
    }


class OrchestratorService:
    def __init__(
        self,
        settings: FleetbaseSettings,
        client: FleetbaseClient | None = None,
        error_handler: ErrorHandler | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or FleetbaseClient(settings)
        self.errors = error_handler or ErrorHandler()

    def run(
        self,
        *,
        order_ids: list[str],
        mode: str = "allocate",
        vehicle_ids: list[str] | None = None,
        driver_ids: list[str] | None = None,
        engine: str | None = None,
        options: dict[str, Any] | None = None,
        prior_assignments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        opts = dict(options or {})
        if engine:
            opts["engine"] = engine
        body: dict[str, Any] = {
            "mode": mode,
            "order_ids": order_ids,
            "options": opts,
        }
        if vehicle_ids:
            body["vehicle_ids"] = vehicle_ids
        if driver_ids:
            body["driver_ids"] = driver_ids
        if prior_assignments:
            body["prior_assignments"] = prior_assignments
        # Legacy adapter shape also accepted order list under "orders"
        body["orders"] = order_ids
        try:
            # Mutate-class solve — worker path only. Never ops_timeout (2s GET budget).
            response = self.client.post(
                RUN_PATH, json=body, timeout=self.settings.request_timeout
            )
        except Exception as exc:
            self.errors.log_and_suppress(exc, "Fleetbase orchestrator run failed")
            hint = None
            if getattr(exc, "status_code", None) == 503:
                hint = "VROOM may be down. Retry with greedy."
            return normalize_run_result(
                {"error": str(exc), "hint": hint, "engine": engine, "assignments": []}
            )
        return normalize_run_result(response if isinstance(response, dict) else {})

    def commit(
        self,
        *,
        assignments: list[dict[str, Any]],
        scheduled_date: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"assignments": assignments}
        if scheduled_date:
            body["scheduled_date"] = scheduled_date
        try:
            response = self.client.post(
                COMMIT_PATH, json=body, timeout=self.settings.ops_timeout
            )
        except Exception as exc:
            self.errors.log_and_suppress(exc, "Fleetbase orchestrator commit failed")
            return normalize_commit_result({"error": str(exc)})
        return normalize_commit_result(response if isinstance(response, dict) else {})

    def list_engines(self) -> list[dict[str, Any]]:
        try:
            response = self.client.get(ENGINES_PATH)
        except Exception as exc:
            self.errors.log_and_suppress(exc, "Fleetbase orchestrator engines list failed")
            return [{"id": "greedy", "name": "Greedy (built-in)"}, {"id": "vroom", "name": "VROOM"}]
        if isinstance(response, dict):
            engines = response.get("engines") or response.get("data") or []
            if isinstance(engines, list):
                return [e for e in engines if isinstance(e, dict)]
        return []
