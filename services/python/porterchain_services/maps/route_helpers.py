"""Shared route geometry builders for tracking and navigation."""

from __future__ import annotations

from typing import Any

from porterchain_services.maps.polyline import valhalla_shape_to_google_polyline


def optimized_route_from_valhalla(result: dict[str, Any] | None) -> dict[str, Any] | None:
    """Normalize a Valhalla /route response for map clients."""
    if not result or "trip" not in result:
        return None
    summary = result.get("trip", {}).get("summary", {})
    legs = result.get("trip", {}).get("legs") or []
    shape = legs[0].get("shape") if legs else None
    return {
        "source": "valhalla",
        "duration_seconds": int(summary.get("time", 0)),
        "distance_meters": int(float(summary.get("length", 0)) * 1000),
        "polyline": valhalla_shape_to_google_polyline(shape),
        "polyline_encoding": "google",
    }
