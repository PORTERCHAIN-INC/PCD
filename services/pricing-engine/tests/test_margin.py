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
    assert margin_check(10000, 0, vehicle_class="sedan_suv").insurance_cents == 0
    over = {"insurance_monthly_cents": {"sedan_suv": 22000}, "working_days_per_month": 20, "working_hours_per_day": 11}
    assert margin_check(10000, 0, vehicle_class="sedan_suv", overrides=over).insurance_cents == round(100 * 18 / 60)
