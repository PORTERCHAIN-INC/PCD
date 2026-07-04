"""Authoritative routing distance for pricing — delegates to MapsService (Valhalla/OSRM)."""

from __future__ import annotations

from porterchain_pricing import GeoPoint, total_route_meters
from porterchain_services.maps.service import MapsService


def _points_from_geo(pickup: GeoPoint, dropoff: GeoPoint, stops: list[GeoPoint]) -> list[tuple[float, float]] | None:
    chain = [pickup, *stops, dropoff]
    pts: list[tuple[float, float]] = []
    for p in chain:
        if p.lat is None or p.lng is None:
            return None
        pts.append((p.lat, p.lng))
    return pts


def resolve_route_distance(
    pickup: GeoPoint,
    dropoff: GeoPoint,
    stops: list[GeoPoint] | None = None,
) -> tuple[int | None, int | None]:
    """Road-network distance via Valhalla/OSRM; haversine fallback when routing unavailable."""
    stops = stops or []
    haversine = total_route_meters(pickup, dropoff, stops)

    points = _points_from_geo(pickup, dropoff, stops)
    if not points:
        return haversine, None

    maps = MapsService()
    meters, seconds = maps.route_distance_meters(points)
    if meters is None:
        return haversine, None
    return meters, seconds
