"""P2-1 zone polygons stay AABB-equivalent for quote fixtures."""

from porterchain_pricing.zone import DEFAULT_ZONES, aabb_polygon


def test_default_zones_have_closed_rectangles():
    for zone in DEFAULT_ZONES:
        assert zone.polygon == aabb_polygon(zone.bounds)
        assert zone.polygon[0] == zone.polygon[-1]
