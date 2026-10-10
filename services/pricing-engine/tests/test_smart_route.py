"""Smart route pricing: every route shape, smooth curve, optimized order, cost floor."""

from __future__ import annotations

from datetime import datetime

import pytest

from porterchain_pricing.gta150_fsa import gta150_fsa_record
from porterchain_pricing.smart_route import (
    RouteStop,
    curve_cents,
    default_smart_pricing,
    haversine_matrix,
    normalize_smart_pricing,
    smart_quote,
)

NOON = datetime(2026, 10, 13, 12, 0)


def road(points):
    km, mins, _ = haversine_matrix(points)
    return km, mins, "valhalla"


def centroid(fsa):
    r = gta150_fsa_record(fsa)
    return (r["lat"], r["lng"]) if r else None


def P(fsa, **kw):
    return RouteStop("pickup", fsa=fsa, label=f"P:{fsa}", **kw)


def D(fsa, parcels=1, **kw):
    return RouteStop(
        "drop", fsa=fsa, label=f"D:{fsa}", parcels=[(5.0, None)] * parcels, **kw
    )


def q(stops, vehicle="cargo_van", **kw):
    return smart_quote(
        stops, vehicle_class=vehicle, matrix=road, centroid=centroid, when=NOON, **kw
    )


@pytest.mark.parametrize(
    "stops,shape",
    [
        ([P("L9T"), D("L5M")], "single_pickup_single_drop"),
        ([P("L9T"), D("L5M"), D("M5V"), D("L6Y")], "single_pickup_multi_drop"),
        ([P("L9T"), P("L5N"), D("M5V")], "multi_pickup_single_drop"),
        ([P("L9T"), P("L5N"), D("M5V"), D("L6Y"), D("L4Z")], "multi_pickup_multi_drop"),
    ],
)
def test_every_shape_prices_with_explanation(stops, shape):
    r = q(stops)
    assert r["shape"] == shape and r["total_cents"] > 0
    assert sum(line["cents"] for line in r["lines"]) == pytest.approx(
        r["total_cents"], abs=len(r["lines"])
    )
    assert r["cost"]["status"] != "below_cost" and r["confidence"] >= 0.9
    assert r["sequence"][0].startswith("P:") and r["sequence"][-1].startswith("D:")
    pick_pos = [i for i, s in enumerate(r["sequence"]) if s.startswith("P:")]
    assert max(pick_pos) < min(
        i for i, s in enumerate(r["sequence"]) if s.startswith("D:")
    )


def test_fsa_mode_same_fsa_pair_same_price_any_address():
    a = q([P("L9T", lat=43.50, lng=-79.88), D("L5M", lat=43.56, lng=-79.72)])
    b = q([P("L9T", lat=43.53, lng=-79.86), D("L5M", lat=43.58, lng=-79.75)])
    assert a["total_cents"] == b["total_cents"]


def test_distance_mode_uses_real_coordinates():
    cfg = {"mode": "distance"}
    near = q(
        [P(None, lat=43.65, lng=-79.38), D(None, lat=43.70, lng=-79.40)], config=cfg
    )
    far = q(
        [P(None, lat=43.65, lng=-79.38), D(None, lat=43.90, lng=-79.60)], config=cfg
    )
    assert far["total_cents"] > near["total_cents"]


def test_miles_unit():
    km = q([P("L9T"), D("M5V")])
    mi = q([P("L9T"), D("M5V")], config={"distance_unit": "mi"})
    assert mi["unit"] == "mi" and mi["route_distance"] == pytest.approx(
        km["route_km"] / 1.609344, abs=0.02
    )


def test_optimized_route_cheaper_than_summing_legs():
    multi = q([P("L9T"), D("L5M"), D("L5N"), D("L5L")])
    legs = sum(q([P("L9T"), D(f)])["total_cents"] for f in ("L5M", "L5N", "L5L"))
    assert multi["total_cents"] < legs
    assert all(m["insertion_km"] >= 0 for m in multi["marginal_stops"])
    assert len(multi["marginal_stops"]) == 3


def test_order_of_input_does_not_change_price():
    a = q([P("L9T"), D("M5V"), D("L5M"), D("L6Y")])
    b = q([P("L9T"), D("L6Y"), D("M5V"), D("L5M")])
    assert a["total_cents"] == b["total_cents"]


def test_curve_is_continuous_and_monotone():
    curve = default_smart_pricing()["distance_curve"]
    prev = -1.0
    for tenth in range(0, 2000):
        v = curve_cents(tenth / 10, curve)
        assert v >= prev
        assert (
            v - prev <= 150 / 10 + 1e-6 or prev < 0
        )  # never jumps more than one unit-step
        prev = v


def test_cost_floor_never_below_cost():
    cheap = {
        "base_cents": 0,
        "distance_curve": [{"from": 0, "cents": 1}],
        "minute_cents": 0,
        "vehicle_minimum_cents": {},
    }
    r = q([P("L9T"), D("L4M")], config=cheap)  # Barrie: long route
    assert any(line["code"] == "cost_floor" for line in r["lines"])
    assert r["cost"]["margin_cents"] >= 0


def test_handling_tiers_and_quote():
    heavy = RouteStop("drop", fsa="L5M", parcels=[(130 * 0.4536, None)])
    r = q([P("L9T"), heavy])
    assert any(
        line["code"] == "handling" and line["cents"] == 6000 for line in r["lines"]
    )
    huge = RouteStop("drop", fsa="L5M", parcels=[(200 * 0.4536, None)])
    assert q([P("L9T"), huge])["custom_quote"] is True


def test_extra_parcels_peak_downtown_and_minimum():
    base = q([P("L9T"), D("L5M", parcels=3)])
    more = q([P("L9T"), D("L5M", parcels=5)])
    assert more["total_cents"] - base["total_cents"] == 2 * 150
    peak = smart_quote(
        [P("L9T"), D("L5M")],
        vehicle_class="cargo_van",
        matrix=road,
        centroid=centroid,
        when=datetime(2026, 10, 13, 8, 0),
    )
    assert peak["total_cents"] > q([P("L9T"), D("L5M")])["total_cents"]
    assert any("downtown" in line["label"] for line in q([P("L9T"), D("M5V")])["lines"])
    tiny = q([P("L5M"), D("L5M")], vehicle="cargo_van")
    assert tiny["total_cents"] >= 4500


def test_haversine_fallback_lowers_confidence():
    r = smart_quote(
        [P("L9T"), D("L5M")],
        vehicle_class="cargo_van",
        matrix=haversine_matrix,
        centroid=centroid,
        when=NOON,
    )
    assert r["confidence"] < 0.9 and r["notes"]


def test_large_route_uses_heuristic_and_keeps_precedence():
    fsas = ["L5M", "L5N", "L5L", "L5B", "L5A", "L4Z", "L4Y", "L6Y", "M5V"]
    r = q([P("L9T"), *[D(f) for f in fsas]])
    assert r["sequence"][0] == "P:L9T" and len(r["sequence"]) == 10


def test_settings_validation_and_contract_override():
    with pytest.raises(ValueError):
        normalize_smart_pricing({"mode": "teleport"})
    base = q([P("L9T"), D("L5M")])
    override = q([P("L9T"), D("L5M")], config={"base_cents": 3500})
    assert override["total_cents"] - base["total_cents"] in (
        2000,
        2000 * 1,
    )  # no factors at noon in L5M
