"""Authoritative routing distance for pricing — delegates to MapsService (Valhalla/OSRM)."""

from __future__ import annotations

import logging
import time
from collections import OrderedDict

from porterchain_pricing import GeoPoint, total_route_meters
from porterchain_services.maps.service import MapsService

logger = logging.getLogger(__name__)


def _points_from_geo(pickup: GeoPoint, dropoff: GeoPoint, stops: list[GeoPoint]) -> list[tuple[float, float]] | None:
    chain = [pickup, *stops, dropoff]
    pts: list[tuple[float, float]] = []
    for p in chain:
        if p.lat is None or p.lng is None:
            return None
        pts.append((p.lat, p.lng))
    return pts


_ROUTE_CACHE: OrderedDict[tuple, tuple[float, int, int | None, str]] = OrderedDict()
_ROUTE_CACHE_MAX = 5000
_ROUTE_CACHE_TTL = 24 * 3600


def _cache_key(points: list) -> tuple:
    return tuple((round(float(p[0]), 4), round(float(p[1]), 4)) for p in points)


def route_cache_clear() -> None:
    _ROUTE_CACHE.clear()


def resolve_route_distance(
    pickup: GeoPoint,
    dropoff: GeoPoint,
    stops: list[GeoPoint] | None = None,
) -> tuple[int | None, int | None, str]:
    """Road-network distance via Valhalla/OSRM; haversine fallback when routing unavailable."""
    stops = stops or []
    haversine = total_route_meters(pickup, dropoff, stops)

    points = _points_from_geo(pickup, dropoff, stops)
    if not points:
        return haversine, None, "haversine"

    key = None
    try:
        key = _cache_key(points)
    except (TypeError, ValueError, IndexError):
        key = None
    hit = _ROUTE_CACHE.get(key) if key is not None else None
    if hit and time.monotonic() - hit[0] < _ROUTE_CACHE_TTL:
        _ROUTE_CACHE.move_to_end(key)
        return hit[1], hit[2], hit[3]

    maps = MapsService()
    meters, seconds, source = maps.route_distance_meters(points)
    if (
        meters is not None
        and haversine
        and haversine >= 1000
        and meters < haversine * 0.9
    ):
        # Outlier (the old 0 km bug): a road can't be shorter than the straight line.
        logger.warning("route_outlier routed=%s straight=%s", meters, haversine)
        meters = None
    if meters is None:
        try:
            from porterchain_api.platform.metrics import note_routing_source

            note_routing_source("haversine")
        except Exception:
            pass
        return haversine, None, "haversine"
    resolved = source or "haversine"
    if key is not None:
        _ROUTE_CACHE[key] = (time.monotonic(), meters, seconds, resolved)
        if len(_ROUTE_CACHE) > _ROUTE_CACHE_MAX:
            _ROUTE_CACHE.popitem(last=False)
    try:
        from porterchain_api.platform.metrics import note_routing_source

        note_routing_source(resolved)
    except Exception:
        pass
    return meters, seconds, resolved


def route_table(
    origin: tuple[float, float], targets: list[tuple[float, float]], *, chunk: int = 100
) -> list[tuple[int | None, int | None]]:
    """Drive (seconds, meters) from one origin to many targets — Valhalla, OSRM fallback.

    Raises ``RuntimeError('routing_unavailable')``; a rate card never falls back to
    straight-line distance.
    """
    maps = MapsService()
    out: list[tuple[int | None, int | None]] = []
    for start in range(0, len(targets), chunk):
        part = targets[start : start + chunk]
        matrix, _source = maps.matrix_durations([origin], part)
        if not matrix or len(matrix[0]) != len(part):
            raise RuntimeError("routing_unavailable")
        out.extend(matrix[0])
    return out
