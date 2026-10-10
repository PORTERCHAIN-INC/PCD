"""Self-hosted map extras: map-matched driver track (breadcrumb history; GPS-policy gated) and the service-area isochrone."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Any

from porterchain_api.driver_models import DriverLocationPing
from porterchain_api.platform.gps_policy import gps_enabled_for
from porterchain_services.maps.service import MapsService
from sqlalchemy.orm import Session

HUB = (43.5183, -79.8774)  # Milton warehouse
_AREA_CACHE: dict[str, tuple[float, Any]] = {}
_AREA_TTL = 24 * 3600


def driver_track(
    db: Session, driver_id: str, minutes: int = 60, maps: Any | None = None
) -> dict[str, Any]:
    """Last ``minutes`` of breadcrumbs, snapped to roads. Empty when live GPS is off."""
    if not gps_enabled_for(driver_id, db):
        return {
            "driver_id": driver_id,
            "gps_enabled": False,
            "path": [],
            "raw": [],
            "source": "off",
        }
    since = datetime.now(UTC) - timedelta(minutes=max(5, min(minutes, 720)))
    rows = (
        db.query(DriverLocationPing)
        .filter(
            DriverLocationPing.driver_id == driver_id,
            DriverLocationPing.created_at >= since,
        )
        .order_by(DriverLocationPing.created_at.asc())
        .limit(500)
        .all()
    )
    # Drop low-accuracy fixes (>100 m) before matching; they cause zig-zags.
    raw = [[r.lat, r.lng] for r in rows if r.accuracy_m is None or r.accuracy_m <= 100]
    matched = (
        (maps or MapsService()).map_match([(p[0], p[1]) for p in raw])
        if len(raw) >= 2
        else None
    )
    return {
        "driver_id": driver_id,
        "gps_enabled": True,
        "raw": raw,
        "path": matched["path"] if matched else raw,
        "distance_m": matched["distance_m"] if matched else None,
        "source": matched["source"] if matched else "raw",
    }


def service_area(
    minutes: list[int] | None = None, maps: Any | None = None
) -> dict[str, Any]:
    """Drive-time rings from the hub (Valhalla isochrone), cached for a day."""
    mins = sorted({int(m) for m in (minutes or [30, 60, 90]) if 5 <= int(m) <= 180})[:4]
    key = ",".join(map(str, mins))
    hit = _AREA_CACHE.get(key)
    if hit and time.monotonic() - hit[0] < _AREA_TTL:
        return hit[1]
    data = (maps or MapsService()).isochrone(
        HUB, contours_minutes=mins, vehicle_class="cargo_van"
    )
    areas = []
    for f in (data or {}).get("features") or []:
        geom = f.get("geometry") or {}
        rings = geom.get("coordinates") or []
        if geom.get("type") == "MultiPolygon":
            rings = [poly[0] for poly in rings]
        elif geom.get("type") == "Polygon":
            rings = [rings[0]] if rings else []
        for ring in rings:
            areas.append(
                {
                    "minutes": int((f.get("properties") or {}).get("contour") or 0),
                    "path": [[c[1], c[0]] for c in ring],
                }
            )
    out = {
        "hub": list(HUB),
        "areas": areas,
        "source": "valhalla" if areas else "unavailable",
    }
    if areas:
        _AREA_CACHE[key] = (time.monotonic(), out)
    return out
