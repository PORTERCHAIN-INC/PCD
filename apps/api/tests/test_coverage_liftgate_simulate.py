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


def test_upgrade_adds_ten_dollar_line(client):  # noqa: F811
    base = _sim(client)
    up = _sim(client, coverage_upgrade=True, declared_value_cents=900_000)
    line = [i for i in up["items"] if i["code"] == "coverage_upgrade"]
    assert line and line[0]["amount_cents"] == 1000
    assert up["subtotal_cents"] - base["subtotal_cents"] >= 1000
    assert up["coverage"]["covered_up_to_cents"] == 2_500_000
    assert up["margin"]["insurance_cents"] > 0


def test_over_max_and_recommendation(client):  # noqa: F811
    assert _sim(client, declared_value_cents=3_000_000)["coverage"]["over_max"] is True
    assert _sim(client, declared_value_cents=50_000, item_category="electronics")["coverage"]["recommended"] == "upgrade"


def test_liftgate_suggested_for_heavy(client):  # noqa: F811
    assert _sim(client, weight_kg=120)["liftgate_suggestion"]["suggest"] is True
    assert _sim(client, weight_kg=5)["liftgate_suggestion"]["suggest"] is False
