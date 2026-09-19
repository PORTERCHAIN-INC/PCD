"""Zone resolution — geographic pricing zones.

P2-1: DEFAULT_ZONES are GeoJSON rectangles that match the historic AABBs
bit-for-bit (inclusive edges). Do not swap these for Valhalla isochrones —
that changes quoted CAD. Coverage UI may use MapsService.isochrone(); CAD must not.
"""

from __future__ import annotations

from porterchain_pricing.types import GeoPoint, PricingContext, ZoneRecord


def aabb_polygon(bounds: dict[str, float]) -> list[list[float]]:
    """Closed GeoJSON ring (lng, lat) for an axis-aligned box."""
    min_lat, max_lat = bounds["min_lat"], bounds["max_lat"]
    min_lng, max_lng = bounds["min_lng"], bounds["max_lng"]
    return [
        [min_lng, min_lat],
        [max_lng, min_lat],
        [max_lng, max_lat],
        [min_lng, max_lat],
        [min_lng, min_lat],
    ]


def _zone(code: str, name: str, bounds: dict[str, float], multiplier: float = 1.0) -> ZoneRecord:
    return ZoneRecord(
        code=code,
        name=name,
        bounds=bounds,
        multiplier=multiplier,
        polygon=aabb_polygon(bounds),
    )


# Default GTA zones — rectangles identical to the previous AABB bounds.
DEFAULT_ZONES: list[ZoneRecord] = [
    _zone("gta_core", "GTA Core", {"min_lat": 43.58, "max_lat": 43.78, "min_lng": -79.55, "max_lng": -79.25}),
    _zone("gta_outer", "GTA Outer", {"min_lat": 43.45, "max_lat": 43.90, "min_lng": -79.75, "max_lng": -79.05}),
    _zone(
        "ontario_extended",
        "Ontario Extended",
        {"min_lat": 42.0, "max_lat": 45.5, "min_lng": -81.0, "max_lng": -78.0},
    ),
]


def _ring_contains(lng: float, lat: float, ring: list[list[float]]) -> bool:
    """Point-in-ring. Axis-aligned rectangles use inclusive AABB (quote parity)."""
    if len(ring) < 4:
        return False
    xs = [p[0] for p in ring[:-1]]
    ys = [p[1] for p in ring[:-1]]
    unique_x = {round(x, 10) for x in xs}
    unique_y = {round(y, 10) for y in ys}
    if len(unique_x) == 2 and len(unique_y) == 2:
        return min(unique_y) <= lat <= max(unique_y) and min(unique_x) <= lng <= max(unique_x)
    # Even-odd ray cast for non-rectangular future polygons.
    inside = False
    j = len(ring) - 1
    for i, point in enumerate(ring):
        xi, yi = point[0], point[1]
        xj, yj = ring[j][0], ring[j][1]
        intersects = (yi > lat) != (yj > lat) and lng < (xj - xi) * (lat - yi) / (yj - yi + 0.0) + xi
        if intersects:
            inside = not inside
        j = i
    return inside


def zone_contains(zone: ZoneRecord, lat: float, lng: float) -> bool:
    if zone.polygon:
        return _ring_contains(lng, lat, zone.polygon)
    b = zone.bounds
    return b["min_lat"] <= lat <= b["max_lat"] and b["min_lng"] <= lng <= b["max_lng"]


class ZoneService:
  def __init__(self, zones: list[ZoneRecord] | None = None) -> None:
      self._zones = zones or DEFAULT_ZONES

  def with_context(self, ctx: PricingContext) -> ZoneService:
      if ctx.zones:
          return ZoneService(ctx.zones)
      return self

  def resolve_zone(self, point: GeoPoint) -> ZoneRecord | None:
      if point.lat is None or point.lng is None:
          return self._zones[0] if self._zones else None
      for zone in self._zones:
          if zone_contains(zone, point.lat, point.lng):
              return zone
      return self._zones[-1] if self._zones else None

  def resolve_lane(self, pickup: GeoPoint, dropoff: GeoPoint, ctx: PricingContext) -> str:
      pickup_zone = self.resolve_zone(pickup)
      dropoff_zone = self.resolve_zone(dropoff)
      pickup_code = pickup_zone.code if pickup_zone else "unknown"
      dropoff_code = dropoff_zone.code if dropoff_zone else "unknown"
      return f"{pickup_code}->{dropoff_code}"

  def zone_multiplier(self, pickup: GeoPoint, dropoff: GeoPoint) -> tuple[str | None, float]:
      pickup_zone = self.resolve_zone(pickup)
      dropoff_zone = self.resolve_zone(dropoff)
      if pickup_zone and dropoff_zone:
          multiplier = max(pickup_zone.multiplier, dropoff_zone.multiplier)
          code = pickup_zone.code if pickup_zone.code == dropoff_zone.code else f"{pickup_zone.code}_{dropoff_zone.code}"
          return code, multiplier
      if pickup_zone:
          return pickup_zone.code, pickup_zone.multiplier
      return None, 1.0
