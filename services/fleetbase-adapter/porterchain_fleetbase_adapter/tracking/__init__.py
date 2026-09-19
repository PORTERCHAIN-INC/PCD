"""Tracking service — live order status + position history from Fleetbase.

Position history is polled via REST (internal positions query). We intentionally
do NOT call Fleetbase `positions/replay` — that pushes onto SocketCluster, which
web apps must never consume.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from porterchain_fleetbase_adapter.client import FleetbaseClient
from porterchain_fleetbase_adapter.config import FleetbaseSettings
from porterchain_fleetbase_adapter.errors import ErrorHandler

logger = logging.getLogger(__name__)

POSITIONS_PATH = "/int/v1/fleet-ops/positions"
GEOFENCE_HISTORY_PATH = "/v1/geofences/driver/{driver_uuid}/history"
_POINT_RE = re.compile(
    r"POINT\s*\(\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*\)",
    re.IGNORECASE,
)


def _extract_list(response: dict[str, Any] | list[Any] | None) -> list[dict[str, Any]]:
    if isinstance(response, list):
        return [v for v in response if isinstance(v, dict)]
    if not isinstance(response, dict):
        return []
    for key in ("positions", "data", "items", "results"):
        value = response.get(key)
        if isinstance(value, list):
            return [v for v in value if isinstance(v, dict)]
    # Laravel paginator
    nested = response.get("data")
    if isinstance(nested, dict):
        return _extract_list(nested)
    return []


def _coords_from_raw(raw: dict[str, Any]) -> tuple[float, float] | None:
    lat = raw.get("latitude", raw.get("lat"))
    lng = raw.get("longitude", raw.get("lng"))
    if lat is not None and lng is not None:
        try:
            return float(lat), float(lng)
        except (TypeError, ValueError):
            pass

    coords = raw.get("coordinates") or raw.get("location") or raw.get("position")
    if isinstance(coords, dict):
        return _coords_from_raw(coords)
    if isinstance(coords, (list, tuple)) and len(coords) >= 2:
        a, b = float(coords[0]), float(coords[1])
        # GeoJSON Point: [lng, lat]
        if abs(a) > 90 and abs(b) <= 90:
            return b, a
        if 40 <= b <= 50 and -140 <= a <= -50:
            return b, a
        return a, b
    if isinstance(coords, str):
        m = _POINT_RE.search(coords)
        if m:
            lng_s, lat_s = m.group(1), m.group(2)
            return float(lat_s), float(lng_s)
    return None


def normalize_position(raw: dict[str, Any]) -> dict[str, Any] | None:
    c = _coords_from_raw(raw)
    if not c:
        return None
    loc = raw.get("location") if isinstance(raw.get("location"), dict) else None
    if loc and not c:
        c = _coords_from_raw(loc)
    if not c:
        return None
    ts = (
        raw.get("created_at")
        or raw.get("recorded_at")
        or raw.get("occurred_at")
        or raw.get("updated_at")
    )
    return {
        "lat": c[0],
        "lng": c[1],
        "heading": raw.get("heading"),
        "speed": raw.get("speed"),
        "recorded_at": ts,
        "id": raw.get("uuid") or raw.get("id") or raw.get("public_id"),
    }


class TrackingService:
    def __init__(
        self,
        settings: FleetbaseSettings,
        client: FleetbaseClient | None = None,
        error_handler: ErrorHandler | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or FleetbaseClient(settings)
        self.errors = error_handler or ErrorHandler()

    def fetch_tracker(self, fleetbase_order_id: str) -> dict[str, Any] | None:
        try:
            return self.client.get(f"/v1/orders/{fleetbase_order_id}/tracker")
        except Exception as exc:
            self.errors.log_and_suppress(exc, f"Fleetbase tracker fetch failed for {fleetbase_order_id}")
            return None

    def fetch_eta(self, fleetbase_order_id: str) -> dict[str, Any] | None:
        try:
            return self.client.get(f"/v1/orders/{fleetbase_order_id}/eta")
        except Exception as exc:
            self.errors.log_and_suppress(exc, f"Fleetbase ETA fetch failed for {fleetbase_order_id}")
            return None

    def build_tracking_snapshot(self, fleetbase_order_id: str) -> dict[str, Any] | None:
        """Aggregate tracker + ETA for Porterchain tracking API."""
        tracker = self.fetch_tracker(fleetbase_order_id)
        if not tracker:
            return None
        eta = self.fetch_eta(fleetbase_order_id)
        return {
            "fleetbase_order_id": fleetbase_order_id,
            "tracker": tracker,
            "eta": eta,
            "status": tracker.get("status") or _deep_get(tracker, "order", "status"),
            "driver": tracker.get("driver") or _deep_get(tracker, "order", "driver"),
            "coordinates": tracker.get("coordinates") or tracker.get("position"),
        }

    def list_positions(
        self,
        *,
        order_uuid: str | None = None,
        subject_uuid: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Breadcrumb trail from Fleetbase Position records (REST, not SocketCluster)."""
        params: dict[str, Any] = {"limit": limit, "sort": "created_at"}
        if order_uuid:
            params["order_uuid"] = order_uuid
        if subject_uuid:
            params["subject_uuid"] = subject_uuid
        try:
            response = self.client.get(POSITIONS_PATH, params=params)
        except Exception as exc:
            self.errors.log_and_suppress(exc, "Fleetbase positions list failed")
            return []
        points: list[dict[str, Any]] = []
        for raw in _extract_list(response):
            p = normalize_position(raw)
            if p:
                points.append(p)
        points.sort(key=lambda p: str(p.get("recorded_at") or ""))
        return points

    def driver_geofence_history(
        self, driver_uuid: str, *, per_page: int = 100
    ) -> list[dict[str, Any]]:
        """Fallback trail from geofence event locations (public API)."""
        try:
            response = self.client.get(
                GEOFENCE_HISTORY_PATH.format(driver_uuid=driver_uuid),
                params={"per_page": per_page},
            )
        except Exception as exc:
            self.errors.log_and_suppress(exc, "Fleetbase geofence driver history failed")
            return []
        rows = _extract_list(response)
        if not rows and isinstance(response, dict):
            data = response.get("data")
            if isinstance(data, dict):
                rows = _extract_list(data.get("data") if "data" in data else data)
            # paginator shape: { data: [...], current_page, ... }
            if isinstance(data, list):
                rows = [v for v in data if isinstance(v, dict)]
        points: list[dict[str, Any]] = []
        for raw in rows:
            loc = raw.get("location") if isinstance(raw.get("location"), dict) else raw
            p = normalize_position(loc if isinstance(loc, dict) else raw)
            if p:
                if not p.get("recorded_at"):
                    p["recorded_at"] = raw.get("occurred_at")
                points.append(p)
        points.sort(key=lambda p: str(p.get("recorded_at") or ""))
        return points

    def position_history(
        self,
        *,
        order_uuid: str | None = None,
        subject_uuid: str | None = None,
        limit: int = 500,
    ) -> dict[str, Any]:
        """Best-effort breadcrumb: positions REST, then geofence event locations."""
        points = self.list_positions(
            order_uuid=order_uuid, subject_uuid=subject_uuid, limit=limit
        )
        if points:
            return {"points": points, "source": "fleetbase_positions"}
        if subject_uuid:
            geo = self.driver_geofence_history(subject_uuid)
            if geo:
                return {"points": geo, "source": "fleetbase_geofence"}
        return {"points": [], "source": "none"}


def _deep_get(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current
