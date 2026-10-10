from porterchain_pricing.margin import distance_outlier, estimate_cost, margin_check

TOR = (43.6487, -79.3817)
HAM = (43.2557, -79.8711)


def test_cost_uses_27_per_hour():
    cost, minutes, labour, vehicle = estimate_cost(0, pickups=1, drops=1)
    assert minutes == 18.0 and labour == 810 and vehicle == 0 and cost == 810


def test_status_levels():
    assert margin_check(100, 20000).status == "below_cost"
    assert margin_check(100000, 20000).status == "ok"
    r = margin_check(4000, 20000)
    assert r.status in {"thin", "below_cost"} and "driver min" in r.explain


def test_outliers():
    assert distance_outlier(0, TOR, HAM) == "road_shorter_than_straight_line"
    assert distance_outlier(68000, TOR, HAM) is None
    assert distance_outlier(400000, TOR, HAM) == "road_over_3x_straight_line"
    assert distance_outlier(1000, TOR, None) == "missing_coordinates"


def test_insurance_spread_per_hour():
    from porterchain_pricing.margin import insurance_cents_per_hour

    assert round(insurance_cents_per_hour("cargo_van"), 2) == round(60000 / 220, 2)
    r = margin_check(10000, 0, vehicle_class="cargo_van")  # 18 min
    assert r.insurance_cents == round(60000 / 220 * 18 / 60) and "insurance" in r.explain
    assert margin_check(10000, 0, vehicle_class="sedan_suv").insurance_cents == round(25000 / 220 * 18 / 60)
    over = {"insurance_monthly_cents": {"sedan_suv": 22000}, "working_days_per_month": 20, "working_hours_per_day": 11}
    assert margin_check(10000, 0, vehicle_class="sedan_suv", overrides=over).insurance_cents == round(100 * 18 / 60)


def test_km_cost_per_vehicle_box_equals_van():
    from porterchain_pricing.margin import km_cents_for

    assert km_cents_for("sedan_suv") == 20 and km_cents_for("cargo_van") == 35 and km_cents_for("box_20") == 35
    r = margin_check(100000, 10000, vehicle_class="sedan_suv")
    assert r.vehicle_cents == round(10 * 1.5 * 20)


def test_coverage_tiers_and_charge():
    from porterchain_pricing.coverage import charge_cents, normalize_coverage, recommend

    assert recommend(100_000)["tier"] == "included"
    assert recommend(240_000)["tier"] == "upgrade"  # near the $2,500 cap
    assert recommend(50_000, "Electronics")["tier"] == "upgrade"
    assert recommend(2_600_000)["tier"] == "over_max"
    assert charge_cents(True, 3) == 1000
    assert charge_cents(True, 3, {"unit": "parcel"}) == 3000
    assert charge_cents(False, 3) == 0
    import pytest

    with pytest.raises(ValueError):
        normalize_coverage({"unit": "box"})


def test_liftgate_suggestion():
    from porterchain_pricing.suggest import suggest_liftgate

    assert suggest_liftgate([{"weight_kg": 80}])["suggest"]
    assert suggest_liftgate([{"weight_kg": 20}])["suggest"] is False
    assert suggest_liftgate(package_type="pallet")["suggest"]
    assert suggest_liftgate([{"weight_kg": 60}], threshold_kg=50)["suggest"]
