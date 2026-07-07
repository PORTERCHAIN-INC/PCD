"""Distance and duration helpers."""

from __future__ import annotations

import math

from porterchain_pricing.catalog import AVG_SPEED_KMH
from porterchain_pricing.types import GeoPoint


def haversine_meters(a: GeoPoint, b: GeoPoint) -> int | None:
    if a.lat is None or a.lng is None or b.lat is None or b.lng is None:
        return None
    r = 6_371_000
    phi1, phi2 = math.radians(a.lat), math.radians(b.lat)
    dphi = math.radians(b.lat - a.lat)
    dlambda = math.radians(b.lng - a.lng)
    x = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return int(2 * r * math.atan2(math.sqrt(x), math.sqrt(1 - x)))


def total_route_meters(pickup: GeoPoint, dropoff: GeoPoint, stops: list[GeoPoint]) -> int | None:
    legs: list[tuple[GeoPoint, GeoPoint]] = [(pickup, dropoff)]
    if stops:
        legs = [(pickup, stops[0])]
        for i in range(len(stops) - 1):
            legs.append((stops[i], stops[i + 1]))
        legs.append((stops[-1], dropoff))

    total = 0
    for start, end in legs:
        leg = haversine_meters(start, end)
        if leg is None:
            return None
        total += leg
    return total


def estimate_duration_minutes(distance_meters: int | None) -> int:
    if not distance_meters:
        return 20
    km = distance_meters / 1000.0
    return max(15, int((km / AVG_SPEED_KMH) * 60))
