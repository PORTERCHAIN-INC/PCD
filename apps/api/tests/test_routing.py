"""Tests for authoritative routing distance resolution."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from porterchain_pricing import GeoPoint

from porterchain_api.services.routing import resolve_route_distance


def test_resolve_route_distance_returns_haversine_when_coords_missing() -> None:
    pickup = GeoPoint(lat=None, lng=None, formatted="Toronto")
    dropoff = GeoPoint(lat=43.65, lng=-79.38, formatted="Dropoff")
    meters, seconds, source = resolve_route_distance(pickup, dropoff)
    assert meters is None
    assert seconds is None
    assert source == "haversine"


@patch("porterchain_api.services.routing.MapsService")
def test_resolve_route_distance_returns_valhalla_source(mock_maps_cls: MagicMock) -> None:
    maps = MagicMock()
    maps.route_distance_meters.return_value = (2500, 600, "valhalla")
    mock_maps_cls.return_value = maps

    pickup = GeoPoint(lat=43.6487, lng=-79.3817)
    dropoff = GeoPoint(lat=43.6532, lng=-79.3832)
    meters, seconds, source = resolve_route_distance(pickup, dropoff)

    assert meters == 2500
    assert seconds == 600
    assert source == "valhalla"


@patch("porterchain_api.services.routing.MapsService")
def test_resolve_route_distance_falls_back_to_haversine(mock_maps_cls: MagicMock) -> None:
    maps = MagicMock()
    maps.route_distance_meters.return_value = (None, None, None)
    mock_maps_cls.return_value = maps

    pickup = GeoPoint(lat=43.6487, lng=-79.3817)
    dropoff = GeoPoint(lat=43.6532, lng=-79.3832)
    meters, seconds, source = resolve_route_distance(pickup, dropoff)

    assert meters is not None
    assert seconds is None
    assert source == "haversine"
