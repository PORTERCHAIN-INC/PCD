"""Coverage upgrade line, over-max flag, liftgate suggestion and margin on the admin simulator."""

from tests.test_pricing_simulate import client  # noqa: F401

PICK = {"lat": 43.6487, "lng": -79.3817, "formatted": "Toronto", "postal": "M5X 1A9"}
DROP = {"lat": 43.7001, "lng": -79.4163, "formatted": "Toronto", "postal": "M5N 1A1"}


def _sim(client, **extra):  # noqa: F811
    body = {"pickup": PICK, "dropoff": DROP, "vehicle_class": "cargo_van", "distance_meters": 9000,
            "use_typed_distance": True, **extra}
    res = client.post("/v1/pricing/simulate", json=body)
    assert res.status_code == 200, res.text
    return res.json()


def test_cover_off_until_g_ins(client):  # noqa: F811
    """Ravi 2026-10-29: declared-value cover is off until cargo insurance is confirmed (G-INS)."""
    base = _sim(client)
    up = _sim(client, coverage_upgrade=True, declared_value_cents=100_000)
    assert not [i for i in up["items"] if i["code"] == "coverage_upgrade"]
    assert up["subtotal_cents"] == base["subtotal_cents"]
    assert up["coverage"]["unavailable"] == ["declared_value_cover_unavailable"]
    assert up["coverage"]["default_liability_cents_per_kg"] == 441


def test_over_max_and_excluded(client):  # noqa: F811
    assert _sim(client, coverage_upgrade=True, declared_value_cents=300_000)["coverage"]["over_max"] is True
    assert _sim(client, declared_value_cents=50_000, item_category="jewellery")["coverage"]["recommended"] == "excluded"


def test_liftgate_suggested_for_heavy(client):  # noqa: F811
    assert _sim(client, weight_kg=120)["liftgate_suggestion"]["suggest"] is True
    assert _sim(client, weight_kg=5)["liftgate_suggestion"]["suggest"] is False
