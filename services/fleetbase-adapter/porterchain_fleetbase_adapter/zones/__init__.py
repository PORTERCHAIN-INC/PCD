"""Zones / service-areas — Fleetbase territory overlays (read-only)."""

from __future__ import annotations

import logging
from typing import Any

from porterchain_fleetbase_adapter.client import FleetbaseClient
from porterchain_fleetbase_adapter.config import FleetbaseSettings
from porterchain_fleetbase_adapter.errors import ErrorHandler

logger = logging.getLogger(__name__)

ZONES_PATH = "/v1/zones"
SERVICE_AREAS_PATH = "/v1/service-areas"


def _extract_list(response: dict[str, Any] | list[Any] | None) -> list[dict[str, Any]]:
    if isinstance(response, list):
        return [v for v in response if isinstance(v, dict)]
    if not isinstance(response, dict):
        return []
    for key in ("zones", "service_areas", "data", "items"):
        value = response.get(key)
        if isinstance(value, list):
            return [v for v in value if isinstance(v, dict)]
    return []


def _ring_from_border(border: Any) -> list[list[float]]:
    """Normalize Fleetbase border geometry → [[lat, lng], ...] ring."""
    if border is None:
        return []
    coords: Any = border
    if isinstance(border, dict):
        coords = border.get("coordinates") or border.get("paths") or border.get("points")
        # GeoJSON Polygon: coordinates = [ ring[ [lng,lat], ... ] ]
        if border.get("type") == "Polygon" and isinstance(coords, list) and coords:
            coords = coords[0]
    if not isinstance(coords, list):
        return []
    ring: list[list[float]] = []
    for pt in coords:
        if isinstance(pt, (list, tuple)) and len(pt) >= 2:
            a, b = float(pt[0]), float(pt[1])
            # GeoJSON is lng,lat — treat |a|>90 as lng-first
            if abs(a) > 90 and abs(b) <= 90:
                ring.append([b, a])
            else:
                # Heuristic: if both look like GTA-ish, prefer lat,lng when first in 40–50
                if 40 <= a <= 50 and -140 <= b <= -50:
                    ring.append([a, b])
                elif 40 <= b <= 50 and -140 <= a <= -50:
                    ring.append([b, a])
                else:
                    ring.append([b, a] if abs(a) > abs(b) else [a, b])
        elif isinstance(pt, dict):
            lat = pt.get("lat", pt.get("latitude"))
            lng = pt.get("lng", pt.get("longitude"))
            if lat is not None and lng is not None:
                ring.append([float(lat), float(lng)])
    return ring


def normalize_zone(raw: dict[str, Any], *, kind: str = "zone") -> dict[str, Any] | None:
    path = _ring_from_border(raw.get("border"))
    if len(path) < 3:
        return None
    return {
        "id": raw.get("id") or raw.get("uuid") or raw.get("public_id"),
        "name": raw.get("name") or kind,
        "kind": kind,
        "color": raw.get("color") or "#2563eb33",
        "stroke_color": raw.get("stroke_color") or raw.get("color") or "#2563eb",
        "path": path,
    }


class ZonesService:
    def __init__(
        self,
        settings: FleetbaseSettings,
        client: FleetbaseClient | None = None,
        error_handler: ErrorHandler | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or FleetbaseClient(settings)
        self.errors = error_handler or ErrorHandler()

    def list_zones(self, *, limit: int = 100) -> list[dict[str, Any]]:
        try:
            response = self.client.get(ZONES_PATH, params={"limit": limit})
        except Exception as exc:
            self.errors.log_and_suppress(exc, "Fleetbase zones list failed")
            return []
        out: list[dict[str, Any]] = []
        for raw in _extract_list(response):
            z = normalize_zone(raw, kind="zone")
            if z:
                out.append(z)
        return out

    def list_service_areas(self, *, limit: int = 50) -> list[dict[str, Any]]:
        try:
            response = self.client.get(SERVICE_AREAS_PATH, params={"limit": limit})
        except Exception as exc:
            self.errors.log_and_suppress(exc, "Fleetbase service-areas list failed")
            return []
        out: list[dict[str, Any]] = []
        for raw in _extract_list(response):
            z = normalize_zone(raw, kind="service_area")
            if z:
                out.append(z)
        return out

    def list_overlays(self) -> list[dict[str, Any]]:
        """Zones first; fall back to service-area borders if zones empty."""
        zones = self.list_zones()
        if zones:
            return zones
        return self.list_service_areas()
