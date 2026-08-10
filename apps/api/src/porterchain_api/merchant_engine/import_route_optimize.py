"""Haversine nearest-neighbor + 2-opt drop reorder for route import (pickup fixed first)."""

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


def _tour_length(pickup: tuple[float, float], drops: list[tuple[float, float]]) -> float:
    if not drops:
        return 0.0
    total = _hav(pickup, drops[0])
    for i in range(len(drops) - 1):
        total += _hav(drops[i], drops[i + 1])
    return total


def _nearest_neighbor(
    start: tuple[float, float], points: list[tuple[float, float]]
) -> list[int]:
    remaining = list(range(len(points)))
    order: list[int] = []
    cur = start
    while remaining:
        best_i = min(remaining, key=lambda i: _hav(cur, points[i]))
        order.append(best_i)
        cur = points[best_i]
        remaining.remove(best_i)
    return order


def _two_opt(pickup: tuple[float, float], points: list[tuple[float, float]], order: list[int]) -> list[int]:
    improved = True
    best = order[:]
    while improved:
        improved = False
        for i in range(len(best) - 1):
            for j in range(i + 1, len(best)):
                cand = best[:i] + best[i : j + 1][::-1] + best[j + 1 :]
                if _tour_length(pickup, [points[k] for k in cand]) + 1e-6 < _tour_length(
                    pickup, [points[k] for k in best]
                ):
                    best = cand
                    improved = True
    return best


def optimize_drop_order(stops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reorder drop stops; keep single pickup first. Returns new stops with updated sequence."""
    pickups = [s for s in stops if s.get("stop_type") == "pickup"]
    drops = [s for s in stops if s.get("stop_type") != "pickup"]
    if not pickups or len(drops) < 2:
        return _renumber(stops)

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
        return _renumber(stops)

    order = _nearest_neighbor(p_coords, drop_coords)
    order = _two_opt(p_coords, drop_coords, order)
    reordered = [usable[i] for i in order] + skipped
    return _renumber([pickup, *reordered])


def _renumber(stops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, s in enumerate(stops):
        row = dict(s)
        row["sequence"] = i + 1
        out.append(row)
    return out
