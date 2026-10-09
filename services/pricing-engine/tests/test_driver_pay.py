"""Driver pay plan — config validation and the pay function (no payouts)."""

from __future__ import annotations

import pytest

from porterchain_pricing.driver_pay import (
    compute_driver_pay,
    default_driver_pay_plan,
    normalize_driver_pay_plan,
)


def _plan(**kw):
    plan = default_driver_pay_plan()
    plan.update(kw)
    return plan


def test_defaults_are_27_an_hour_and_4_hour_blocks():
    plan = normalize_driver_pay_plan(None)
    assert plan["hourly_cents"] == 2700
    assert plan["wave_block"]["block_hours"] == 4
    assert plan["wave_block"]["block_cents"] == 4 * 2700


def test_hourly():
    assert compute_driver_pay(_plan(mode="hourly"), paid_minutes=90).total_cents == 4050
    floor = _plan(mode="hourly", minimum_paid_hours=3)
    assert compute_driver_pay(floor, paid_minutes=60).total_cents == 3 * 2700


def test_per_stop_and_pickup():
    plan = _plan(mode="per_stop", per_stop_cents=800, per_pickup_cents=300)
    assert compute_driver_pay(plan, stops=4, pickups=1).total_cents == 4 * 800 + 300


def test_per_route_with_extra_stops():
    plan = _plan(mode="per_route", per_route_cents=10000, route_included_stops=4, route_extra_stop_cents=700)
    assert compute_driver_pay(plan, stops=4, routes=1).total_cents == 10000
    assert compute_driver_pay(plan, stops=6, routes=1).total_cents == 10000 + 2 * 700


def test_wave_block_by_time_and_given_blocks():
    plan = _plan(mode="wave_block")
    # A 4-stop day in 3 h is one 4 h block, not 8 paid hours.
    assert compute_driver_pay(plan, paid_minutes=180, stops=4).total_cents == 10800
    assert compute_driver_pay(plan, paid_minutes=300, stops=8).total_cents == 2 * 10800
    assert compute_driver_pay(plan, blocks=3).total_cents == 3 * 10800
    assert compute_driver_pay(plan).total_cents == 0


def test_wave_block_extra_stops():
    plan = _plan(mode="wave_block", wave_block={"block_hours": 4, "block_cents": 10800, "included_stops": 4, "extra_stop_cents": 500})
    assert compute_driver_pay(plan, paid_minutes=200, stops=6).total_cents == 10800 + 2 * 500


def test_hybrid_takes_the_higher():
    plan = _plan(mode="hybrid", per_stop_cents=1000)
    assert compute_driver_pay(plan, paid_minutes=60, stops=4).total_cents == 4000
    assert compute_driver_pay(plan, paid_minutes=240, stops=4).total_cents == 4 * 2700


@pytest.mark.parametrize(
    "bad",
    [{"mode": "salary"}, {"hourly_cents": -1}, {"wave_block": {"block_hours": 0}}, {"per_stop_cents": "x"}],
)
def test_invalid_plans(bad):
    with pytest.raises(ValueError, match="driver_pay_invalid"):
        normalize_driver_pay_plan(bad)
