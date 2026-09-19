"""Position history normalize + zone border rings (P2-2 / P2-3)."""

from __future__ import annotations

from porterchain_fleetbase_adapter.tracking import normalize_position
from porterchain_fleetbase_adapter.zones import _ring_from_border, normalize_zone


def test_normalize_position_lat_lng():
    p = normalize_position({"latitude": 43.65, "longitude": -79.38, "created_at": "t"})
    assert p is not None
    assert p["lat"] == 43.65
    assert p["lng"] == -79.38


def test_normalize_position_geojson_point():
    p = normalize_position({"coordinates": [-79.38, 43.65]})
    assert p is not None
    assert abs(p["lat"] - 43.65) < 1e-6
    assert abs(p["lng"] + 79.38) < 1e-6


def test_normalize_position_wkt():
    p = normalize_position({"coordinates": "POINT(-79.38 43.65)"})
    assert p is not None
    assert abs(p["lat"] - 43.65) < 1e-6


def test_ring_from_geojson_polygon():
    ring = _ring_from_border(
        {
            "type": "Polygon",
            "coordinates": [
                [
                    [-79.5, 43.6],
                    [-79.3, 43.6],
                    [-79.3, 43.7],
                    [-79.5, 43.7],
                    [-79.5, 43.6],
                ]
            ],
        }
    )
    assert len(ring) == 5
    assert ring[0][0] == 43.6  # lat
    assert ring[0][1] == -79.5  # lng


def test_normalize_zone_requires_ring():
    assert normalize_zone({"name": "empty", "border": None}) is None
    z = normalize_zone(
        {
            "id": "z1",
            "name": "Downtown",
            "color": "#00f",
            "border": {
                "type": "Polygon",
                "coordinates": [[[-79.5, 43.6], [-79.3, 43.6], [-79.3, 43.7], [-79.5, 43.6]]],
            },
        }
    )
    assert z is not None
    assert z["name"] == "Downtown"
    assert len(z["path"]) >= 3
