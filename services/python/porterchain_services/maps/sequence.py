"""Drop reorder — one Valhalla/OSRM matrix + labeled nearest-neighbor.

Pickup stays first. No 2-opt / TSP. Haversine only when the matrix is down.
Belongs in Maps helpers, not merchant/admin engines.
"""

from __future__ import annotations

import math
from typing import Any

_EARTH_M = 6_371_000


def _coords(stop: dict[str, Any]) -> tuple[float, float] | None:
    lat, lng = stop.get("lat"), stop.get("lng")
    if lat is None or lng is None:
        return None
    return float(lat), float(lng)


def _hav(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return _EARTH_M * 2 * math.asin(min(1.0, math.sqrt(h)))


def _road_costs(
    maps: Any, points: list[tuple[float, float]]
) -> tuple[list[list[float]] | None, str | None]:
    if maps is None:
        try:
            from porterchain_services.maps.service import MapsService

            maps = MapsService()
        except Exception:
            return None, None
    try:
        matrix, source = maps.matrix_durations(points, points)
    except Exception:
        return None, None
    n = len(points)
    if not matrix or len(matrix) != n:
        return None, None
    out: list[list[float]] = []
    for i, row in enumerate(matrix):
        if not isinstance(row, list) or len(row) != n:
            return None, None
        parsed: list[float] = []
        for j, cell in enumerate(row):
            if i == j:
                parsed.append(0.0)
                continue
            seconds, meters = cell if isinstance(cell, tuple) else (None, None)
            if meters is not None:
                parsed.append(float(meters))
            elif seconds is not None:
                parsed.append(float(seconds) * 8.33)
            else:
                return None, None
        out.append(parsed)
    return out, source or "valhalla"


def _nearest_neighbor(
    points: list[tuple[float, float]],
    road: list[list[float]] | None,
) -> list[int]:
    remaining = list(range(len(points) - 1))
    order: list[int] = []
    cur = 0
    while remaining:
        def cost(drop_i: int) -> float:
            nxt = drop_i + 1
            if road is not None:
                return road[cur][nxt]
            return _hav(points[cur], points[nxt])

        best_i = min(remaining, key=cost)
        order.append(best_i)
        cur = best_i + 1
        remaining.remove(best_i)
    return order


def optimize_drop_order_with_source(
    stops: list[dict[str, Any]],
    *,
    maps: Any = None,
) -> tuple[list[dict[str, Any]], str]:
    """Reorder drop stops; keep single pickup first. Source is valhalla/osrm/haversine."""
    pickups = [s for s in stops if s.get("stop_type") == "pickup"]
    drops = [s for s in stops if s.get("stop_type") != "pickup"]
    if not pickups or len(drops) < 2:
        return _renumber(stops), "none"

    pickup = pickups[0]
    p_coords = _coords(pickup)
    drop_coords: list[tuple[float, float]] = []
    usable: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for d in drops:
        c = _coords(d)
        if c is None or p_coords is None:
            skipped.append(d)
        else:
            drop_coords.append(c)
            usable.append(d)

    if p_coords is None or len(usable) < 2:
        return _renumber(stops), "none"

    points = [p_coords, *drop_coords]
    road, source = _road_costs(maps, points)
    if road is None:
        source = "haversine"

    order = _nearest_neighbor(points, road)
    reordered = [usable[i] for i in order] + skipped
    return _renumber([pickup, *reordered]), source or "haversine"


def optimize_drop_order(stops: list[dict[str, Any]], *, maps: Any = None) -> list[dict[str, Any]]:
    """Reorder drop stops; keep single pickup first. Returns new stops with updated sequence."""
    ordered, _source = optimize_drop_order_with_source(stops, maps=maps)
    return ordered


def _renumber(stops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, s in enumerate(stops):
        row = dict(s)
        row["sequence"] = i + 1
        out.append(row)
    return out
