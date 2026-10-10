"""API adapter for smart route pricing: settings, per-merchant opt-in, road matrix."""

from __future__ import annotations

import time
from collections import OrderedDict
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from porterchain_pricing.components.fsa import fsa_from_point
from porterchain_pricing.contract_schedule import deep_merge
from porterchain_pricing.gta150_fsa import gta150_fsa_record
from porterchain_pricing.smart_route import (
    RouteStop,
    haversine_matrix,
    normalize_smart_pricing,
    smart_quote,
)
from sqlalchemy.orm import Session

from porterchain_api.admin_models import SystemConfig
from porterchain_api.merchant_models import Merchant
from porterchain_api.pricing_engine.margin_settings import load_margin_estimates

_TZ = ZoneInfo("America/Toronto")
_MATRIX_CACHE: OrderedDict[tuple, tuple[float, Any]] = OrderedDict()
_MATRIX_TTL = 7 * 24 * 3600  # FSA centroids don't move; a week is safe
_MATRIX_MAX = 2000


def matrix_cache_clear() -> None:
    _MATRIX_CACHE.clear()


def road_matrix(points: list[tuple[float, float]]):
    """All-pairs road km / minutes: Valhalla, OSRM fallback, cached; haversine last resort."""
    key = tuple((round(a, 4), round(b, 4)) for a, b in points)
    hit = _MATRIX_CACHE.get(key)
    if hit and time.monotonic() - hit[0] < _MATRIX_TTL:
        km, mins, _src = hit[1]
        return km, mins, "cache"
    try:
        from porterchain_services.maps.service import MapsService

        cells, source = MapsService().matrix_durations(
            points, points, vehicle_class="cargo_van"
        )
    except Exception:  # noqa: BLE001 — routing outage must not break quoting
        cells, source = [], None
    if (
        not cells
        or len(cells) != len(points)
        or any(c[1] is None for row in cells for c in row)
    ):
        return haversine_matrix(points)
    km = [[(c[1] or 0) / 1000 for c in row] for row in cells]
    mins = [[(c[0] or 0) / 60 for c in row] for row in cells]
    _MATRIX_CACHE[key] = (time.monotonic(), (km, mins, source))
    if len(_MATRIX_CACHE) > _MATRIX_MAX:
        _MATRIX_CACHE.popitem(last=False)
    return km, mins, source or "osrm"


def centroid(fsa: str) -> tuple[float, float] | None:
    rec = gta150_fsa_record(fsa)
    src = (rec or {}).get("centroid") or rec or {}
    if src.get("lat") is None or src.get("lng") is None:
        return None
    return (float(src["lat"]), float(src["lng"]))


def smart_config(db: Session, merchant: Merchant | None = None) -> dict[str, Any]:
    row = db.get(SystemConfig, "smart_pricing")
    try:
        cfg = normalize_smart_pricing(row.value if row else None)
    except ValueError:
        cfg = normalize_smart_pricing(None)
    own = (
        ((merchant.pricing_config or {}).get("smart_pricing") or {}) if merchant else {}
    )
    if isinstance(own, dict) and own:
        cfg = normalize_smart_pricing(
            deep_merge(
                cfg,
                {
                    **(own.get("overrides") or {}),
                    "enabled": own.get("enabled", cfg["enabled"]),
                },
            )
        )
    return cfg


def merchant_opted_in(db: Session, merchant: Merchant | None) -> bool:
    """Live prices change only for merchants switched on (or when the global switch is on)."""
    return bool(smart_config(db, merchant)["enabled"])


def _stop(
    kind: str, point: Any, parcels: list | None = None, label: str | None = None
) -> RouteStop:
    return RouteStop(
        kind,
        lat=getattr(point, "lat", None),
        lng=getattr(point, "lng", None),
        fsa=fsa_from_point(point) or None,
        parcels=list(parcels or [(None, None)]),
        label=label,
    )


def quote_route(
    db: Session,
    *,
    pickups: list[Any],
    drops: list[Any],
    vehicle_class: str,
    merchant_id: str | None = None,
    drop_parcels: list[list] | None = None,
    when: datetime | None = None,
    config_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    merchant = db.get(Merchant, merchant_id) if merchant_id else None
    cfg = smart_config(db, merchant)
    if config_override:
        cfg = deep_merge(cfg, config_override)
    stops = [_stop("pickup", p, label=f"P{i + 1}") for i, p in enumerate(pickups)]
    stops += [
        _stop(
            "drop",
            d,
            (drop_parcels or [])[i] if drop_parcels and i < len(drop_parcels) else None,
            f"D{i + 1}",
        )
        for i, d in enumerate(drops)
    ]
    return smart_quote(
        stops,
        vehicle_class=vehicle_class or "cargo_van",
        matrix=road_matrix,
        config=cfg,
        cost_overrides=load_margin_estimates(db),
        centroid=centroid,
        when=when or datetime.now(_TZ).replace(tzinfo=None),
    )
