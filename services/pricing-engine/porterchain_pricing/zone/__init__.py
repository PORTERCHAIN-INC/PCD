"""Zone resolution — geographic pricing zones."""

from __future__ import annotations

from porterchain_pricing.types import GeoPoint, PricingContext, ZoneRecord

# Default GTA zones (simplified bounding boxes)
DEFAULT_ZONES: list[ZoneRecord] = [
    ZoneRecord(
        code="gta_core",
        name="GTA Core",
        bounds={"min_lat": 43.58, "max_lat": 43.78, "min_lng": -79.55, "max_lng": -79.25},
        multiplier=1.0,
    ),
    ZoneRecord(
        code="gta_outer",
        name="GTA Outer",
        bounds={"min_lat": 43.45, "max_lat": 43.90, "min_lng": -79.75, "max_lng": -79.05},
        multiplier=1.0,
    ),
    ZoneRecord(
        code="ontario_extended",
        name="Ontario Extended",
        bounds={"min_lat": 42.0, "max_lat": 45.5, "min_lng": -81.0, "max_lng": -78.0},
        multiplier=1.0,
    ),
]


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
          b = zone.bounds
          if (
              b["min_lat"] <= point.lat <= b["max_lat"]
              and b["min_lng"] <= point.lng <= b["max_lng"]
          ):
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
