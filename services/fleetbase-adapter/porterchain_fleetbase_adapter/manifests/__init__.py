"""Manifest service — Fleetbase ManifestController (list/show/cancel).

Manifests are created by orchestrator commit (vehicle-scoped execution plans),
not by this service. Paths are `/int/v1/fleet-ops/manifests*` (session/company
scoped upstream); failures degrade to empty lists so ops UI stays usable.
"""

from __future__ import annotations

import logging
from typing import Any

from porterchain_fleetbase_adapter.client import FleetbaseClient
from porterchain_fleetbase_adapter.config import FleetbaseSettings
from porterchain_fleetbase_adapter.errors import ErrorHandler

logger = logging.getLogger(__name__)

LIST_PATH = "/int/v1/fleet-ops/manifests"
DETAIL_PATH = "/int/v1/fleet-ops/manifests/{id}"
CANCEL_PATH = "/int/v1/fleet-ops/manifests/{id}/cancel"


def _extract_list(response: dict[str, Any] | list[Any] | None) -> list[dict[str, Any]]:
    if isinstance(response, list):
        return [v for v in response if isinstance(v, dict)]
    if not isinstance(response, dict):
        return []
    for key in ("manifests", "data", "items"):
        value = response.get(key)
        if isinstance(value, list):
            return [v for v in value if isinstance(v, dict)]
    return []


def normalize_manifest(raw: dict[str, Any]) -> dict[str, Any]:
    """Flatten common Fleetbase manifest shapes for Porterchain ops."""
    stops_raw = raw.get("stops") or raw.get("manifest_stops") or []
    stops: list[dict[str, Any]] = []
    if isinstance(stops_raw, list):
        for i, s in enumerate(stops_raw):
            if not isinstance(s, dict):
                continue
            stops.append(
                {
                    "id": s.get("id") or s.get("uuid") or s.get("public_id"),
                    "sequence": s.get("sequence", i),
                    "status": s.get("status"),
                    "order_id": s.get("order_uuid") or s.get("order_id") or (s.get("order") or {}).get("id"),
                    "place": s.get("place") or s.get("address"),
                    "waypoint_id": s.get("waypoint_uuid") or s.get("waypoint_id"),
                }
            )
    driver = raw.get("driver") if isinstance(raw.get("driver"), dict) else {}
    vehicle = raw.get("vehicle") if isinstance(raw.get("vehicle"), dict) else {}
    return {
        "id": raw.get("id") or raw.get("uuid") or raw.get("public_id"),
        "public_id": raw.get("public_id") or raw.get("id"),
        "status": raw.get("status"),
        "scheduled_date": raw.get("scheduled_date") or raw.get("date"),
        "driver_id": raw.get("driver_uuid") or raw.get("driver_id") or driver.get("id"),
        "driver_name": driver.get("name") or driver.get("full_name"),
        "vehicle_id": raw.get("vehicle_uuid") or raw.get("vehicle_id") or vehicle.get("id"),
        "vehicle_name": vehicle.get("name") or vehicle.get("plate_number") or vehicle.get("display_name"),
        "stop_count": len(stops) if stops else raw.get("stop_count") or raw.get("stops_count"),
        "stops": stops,
        "meta": raw.get("meta") if isinstance(raw.get("meta"), dict) else {},
    }


class ManifestService:
    def __init__(
        self,
        settings: FleetbaseSettings,
        client: FleetbaseClient | None = None,
        error_handler: ErrorHandler | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or FleetbaseClient(settings)
        self.errors = error_handler or ErrorHandler()

    def list(
        self,
        *,
        scheduled_date: str | None = None,
        status: str | None = None,
        driver_id: str | None = None,
        vehicle_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if scheduled_date:
            params["scheduled_date"] = scheduled_date
        if status:
            params["status"] = status
        if driver_id:
            params["driver_id"] = driver_id
        if vehicle_id:
            params["vehicle_id"] = vehicle_id
        try:
            response = self.client.get(LIST_PATH, params=params)
        except Exception as exc:
            self.errors.log_and_suppress(exc, "Fleetbase manifest list failed")
            return []
        return [normalize_manifest(m) for m in _extract_list(response)]

    def get(self, manifest_id: str) -> dict[str, Any] | None:
        try:
            response = self.client.get(DETAIL_PATH.format(id=manifest_id))
        except Exception as exc:
            self.errors.log_and_suppress(exc, f"Fleetbase manifest fetch failed for {manifest_id}")
            return None
        if not isinstance(response, dict):
            return None
        body = response.get("manifest") if isinstance(response.get("manifest"), dict) else response
        if not isinstance(body, dict):
            return None
        return normalize_manifest(body)

    def cancel(self, manifest_id: str) -> bool:
        try:
            self.client.post(CANCEL_PATH.format(id=manifest_id), json={})
            return True
        except Exception as exc:
            self.errors.log_and_suppress(exc, f"Fleetbase manifest cancel failed for {manifest_id}")
            return False
