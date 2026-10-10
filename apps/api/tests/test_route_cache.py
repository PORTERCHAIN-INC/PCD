from unittest.mock import patch

from porterchain_api.services import routing
from porterchain_pricing import GeoPoint

TOR = GeoPoint(lat=43.6487, lng=-79.3817, formatted="", postal="")
HAM = GeoPoint(lat=43.2557, lng=-79.8711, formatted="", postal="")


def test_cache_and_outlier():
    routing.route_cache_clear()
    with patch.object(
        routing.MapsService,
        "route_distance_meters",
        return_value=(68000, 3600, "valhalla"),
    ) as m:
        assert routing.resolve_route_distance(TOR, HAM)[0] == 68000
        assert routing.resolve_route_distance(TOR, HAM)[0] == 68000
        assert m.call_count == 1
    routing.route_cache_clear()
    with patch.object(
        routing.MapsService, "route_distance_meters", return_value=(0, 0, "valhalla")
    ):
        meters, _s, source = routing.resolve_route_distance(TOR, HAM)
        assert source == "haversine" and meters > 50000
    routing.route_cache_clear()
