"""Tests for public tracking snapshot enrichment."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from porterchain_services.maps.polyline import encode_polyline
from porterchain_api.booking_engine.public_tracking_snapshot import build_public_live_tracking
from porterchain_api.booking_models import Order


def _order(**kwargs) -> Order:
    defaults = {
        "id": "ord-1",
        "tracking_number": "PC-TEST01",
        "state": "IN_TRANSIT",
        "scheduled_at": datetime(2026, 7, 8, 18, 0, tzinfo=UTC),
        "pickup": {"formatted": "1 King St W", "lat": 43.6487, "lng": -79.3817},
        "dropoff": {"formatted": "100 Queen St W", "lat": 43.6532, "lng": -79.3832},
    }
    defaults.update(kwargs)
    order = Order()
    for key, value in defaults.items():
        setattr(order, key, value)
    return order


def test_build_public_live_tracking_scheduled_fallback():
    maps = MagicMock()
    maps.eta_between.return_value = None
    maps.optimized_route.return_value = None
    order = _order()
    snapshot = build_public_live_tracking(order, None, maps=maps)

    assert snapshot["pickup"]["lat"] == 43.6487
    assert snapshot["pickup"]["lng"] == -79.3817
    assert snapshot["eta"]["source"] == "scheduled"
    assert snapshot["eta"]["arrives_at"]
    assert snapshot["delivery_status"]["in_transit"] is True


def test_build_public_live_tracking_osrm_eta():
    maps = MagicMock()
    maps.eta_between.return_value = {
        "source": "osrm",
        "duration_seconds": 600,
        "distance_meters": 2500,
        "polyline": "abc",
    }
    maps.optimized_route.return_value = {
        "source": "valhalla",
        "duration_seconds": 700,
        "distance_meters": 2500,
        "polyline": encode_polyline([(43.6487, -79.3817), (43.6532, -79.3832)], precision=5),
        "polyline_encoding": "google",
    }

    live_raw = {
        "tracker": {"status": "in_transit"},
        "coordinates": {"lat": 43.65, "lng": -79.38},
    }
    snapshot = build_public_live_tracking(_order(), live_raw, maps=maps)

    assert snapshot["eta"]["source"] == "osrm"
    assert snapshot["eta"]["label"] == "10 min"
    assert snapshot["driver_location"] == {"lat": 43.65, "lng": -79.38}
    assert snapshot["optimized_route"]["polyline_encoding"] == "google"
    assert snapshot["optimized_route"]["polyline"] is not None


def test_build_public_live_tracking_hides_eta_when_delivered():
    maps = MagicMock()
    snapshot = build_public_live_tracking(_order(state="DELIVERED"), None, maps=maps)

    assert snapshot["eta"] is None
    assert snapshot["delivery_status"]["delivered"] is True
