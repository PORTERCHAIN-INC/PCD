"""Fuel / km scorecard for optimize metrics (pricing_fuel × distance)."""

from __future__ import annotations

from unittest.mock import MagicMock

from porterchain_pricing.fuel_scorecard import (
    enrich_optimize_metrics_fuel,
    fuel_delta,
    fuel_scorecard,
    liters_per_100km_for_class,
)
from porterchain_pricing.types import FuelConfig


def test_liters_per_100km_box_higher_than_van() -> None:
    assert liters_per_100km_for_class("box_truck") > liters_per_100km_for_class(
        "cargo_van"
    )


def test_fuel_scorecard_cents() -> None:
    # 100 km × 22 L/100km × $1.58/L = 34.76 → 3476 cents
    out = fuel_scorecard(
        distance_km=100.0,
        fuel_price_cents_per_liter=158,
        liters_per_100km=22.0,
    )
    assert out["estimated_fuel_liters"] == 22.0
    assert out["estimated_fuel_cents"] == 3476
    assert out["cents_per_km"] == 34.76


def test_enrich_and_delta() -> None:
    fuel = FuelConfig(current_fuel_price_cents=158)
    metrics = enrich_optimize_metrics_fuel(
        {"after_distance_km": 40.0, "before_distance_km": 50.0},
        fuel=fuel,
        vehicle_class="cargo_van",
    )
    assert metrics["estimated_fuel_liters"] > 0
    assert metrics["fuel_delta_cents"] > 0
    assert metrics["distance_delta_km"] == 10.0

    delta = fuel_delta(
        before_km=50.0, after_km=40.0, fuel=fuel, vehicle_class="cargo_van"
    )
    assert delta["fuel_delta_cents"] == metrics["fuel_delta_cents"]
    assert delta["fuel_delta_liters"] > 0


def test_get_fuel_delta_tool_explicit_km() -> None:
    from porterchain_api.intelligence_engine.tools import get_fuel_delta

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    out = get_fuel_delta(db, before_km=50.0, after_km=40.0, vehicle_class="box_truck")
    assert out["tool"] == "get_fuel_delta"
    assert out["fuel_delta_cents"] > 0
    assert out["distance_delta_km"] == 10.0
