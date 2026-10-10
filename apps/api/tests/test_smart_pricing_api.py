"""Smart route pricing through the admin simulator — every shape, old vs new side by side."""

from __future__ import annotations

import pytest

from porterchain_api.pricing_engine import smart_pricing
from tests.test_pricing_simulate import client  # noqa: F401


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    smart_pricing.matrix_cache_clear()

    class Maps:
        def matrix_durations(self, sources, targets, **kw):
            from porterchain_pricing.smart_route import haversine_matrix

            km, mins, _ = haversine_matrix(sources)
            return [
                [(int(m * 60), int(k * 1000)) for k, m in zip(kr, mr)]
                for kr, mr in zip(km, mins)
            ], "valhalla"

    import porterchain_services.maps.service as svc

    monkeypatch.setattr(svc, "MapsService", Maps)


def _pt(postal, lat, lng):
    return {"postal": postal, "lat": lat, "lng": lng, "formatted": f"{postal}, ON"}


MILTON = _pt("L9T 1A1", 43.51, -79.88)
MISS = _pt("L5M 1A1", 43.56, -79.72)
TOR = _pt("M5V 1A1", 43.64, -79.39)
BRAM = _pt("L6Y 1A1", 43.67, -79.75)


@pytest.mark.parametrize(
    "extra_p,extra_d,shape",
    [
        ([], [], "single_pickup_single_drop"),
        ([], [TOR, BRAM], "single_pickup_multi_drop"),
        ([BRAM], [], "multi_pickup_single_drop"),
        ([BRAM], [TOR], "multi_pickup_multi_drop"),
    ],
)
def test_simulator_returns_old_and_new(client, extra_p, extra_d, shape):  # noqa: F811
    r = client.post(
        "/v1/pricing/simulate",
        json={
            "pickup": MILTON,
            "dropoff": MISS,
            "vehicle_class": "cargo_van",
            "use_typed_distance": True,
            "distance_meters": 20000,
            "extra_pickups": extra_p,
            "extra_drops": extra_d,
        },
    )
    assert r.status_code == 200, r.text
    smart = r.json()["smart"]
    assert smart["shape"] == shape and smart["total_cents"] > 0
    assert smart["current_cents"] == r.json()["subtotal_cents"]
    assert (
        smart["matrix_source"] in ("valhalla", "cache") and smart["confidence"] >= 0.9
    )


def test_matrix_is_cached():
    pts = [(43.51, -79.88), (43.56, -79.72)]
    assert smart_pricing.road_matrix(pts)[2] == "valhalla"
    assert smart_pricing.road_matrix(pts)[2] == "cache"


def test_routing_outage_falls_back(monkeypatch):
    import porterchain_services.maps.service as svc

    class Down:
        def matrix_durations(self, *a, **k):
            return [], None

    monkeypatch.setattr(svc, "MapsService", Down)
    smart_pricing.matrix_cache_clear()
    assert smart_pricing.road_matrix([(43.5, -79.8), (43.6, -79.7)])[2] == "haversine"
