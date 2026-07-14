"""Rate card defaults and merchant overlays drive quote math."""

from __future__ import annotations

from datetime import UTC, datetime

from porterchain_pricing.engine import PricingEngine
from porterchain_pricing.rate_card import RateCard, VehicleRate, default_rate_card, merge_merchant_overlay
from porterchain_pricing.types import GeoPoint, PricingContext, PricingRequest


def _req(**kwargs) -> PricingRequest:
    base = dict(
        pickup=GeoPoint(lat=43.65, lng=-79.38, formatted="Toronto"),
        dropoff=GeoPoint(lat=43.70, lng=-79.40, formatted="North York"),
        vehicle_class="cargoVan",
        distance_meters=10_000,
        estimated_duration_minutes=20,
        scheduled_at=datetime(2026, 7, 13, 12, 0, tzinfo=UTC),  # Monday
    )
    base.update(kwargs)
    return PricingRequest(**base)


def test_default_rate_card_matches_catalog_floor():
    card = default_rate_card()
    assert card.vehicle("sedan").per_km_cents == 100
    assert card.liftgate_cents == 4500


def test_system_rate_card_changes_per_km():
    card = default_rate_card()
    card.vehicles["cargoVan"] = VehicleRate(per_km_cents=250, minimum_cents=100, surcharge_cents=0)
    engine = PricingEngine()
    ctx = PricingContext(rate_card=card)
    breakdown = engine.calculate(_req(channel="retail"), ctx)
    # 10 km * 250¢ = 2500
    assert breakdown.distance_cents == 2500
    assert breakdown.base_cents == 2500


def test_merchant_overlay_raises_minimum():
    system = default_rate_card()
    effective = merge_merchant_overlay(
        system,
        {"rate_card": {"vehicles": {"cargoVan": {"per_km_cents": 100, "minimum_cents": 5000, "surcharge_cents": 0}}}},
    )
    engine = PricingEngine()
    breakdown = engine.calculate(_req(channel="retail", distance_meters=1000), PricingContext(rate_card=effective))
    assert breakdown.final_cents >= 5000


def test_per_minute_and_wait_and_extra_stop():
    card = default_rate_card()
    card.per_minute_cents = 50
    card.wait_cents_per_minute = 100
    card.extra_stop_cents = 300
    engine = PricingEngine()
    breakdown = engine.calculate(
        _req(
            estimated_duration_minutes=10,
            wait_minutes=5,
            additional_stops=[GeoPoint(lat=43.68, lng=-79.39)],
        ),
        PricingContext(rate_card=card),
    )
    codes = {i.code: i.amount_cents for i in breakdown.items}
    assert codes.get("per_minute") == 500
    assert codes.get("wait") == 500
    assert codes.get("additional_stops") == 300


def test_weekend_multiplier_from_rate_card():
    card = default_rate_card()
    card.weekend_multiplier = 1.5
    engine = PricingEngine()
    weekend = _req(scheduled_at=datetime(2026, 7, 11, 12, 0, tzinfo=UTC))  # Saturday
    breakdown = engine.calculate(weekend, PricingContext(rate_card=card))
    assert any(i.code == "weekend" for i in breakdown.items)


def test_share_pct_in_metadata():
    card = RateCard(driver_share_pct=70, platform_share_pct=30)
    # refill vehicles from default
    card.vehicles = default_rate_card().vehicles
    engine = PricingEngine()
    breakdown = engine.calculate(_req(), PricingContext(rate_card=card))
    assert breakdown.metadata["driver_share_pct"] == 70
    assert breakdown.metadata["platform_share_pct"] == 30


def test_driver_payout_flat_and_percent():
    flat = default_rate_card()
    assert flat.driver_payout_mode == "flat"
    assert flat.compute_driver_payout_cents() == 850

    flat.driver_flat_per_delivery_cents = 1200
    flat.driver_minimum_payout_cents = 1500
    assert flat.compute_driver_payout_cents() == 1500  # floor

    pct = default_rate_card()
    pct.driver_payout_mode = "percent"
    pct.driver_share_pct = 70
    pct.driver_minimum_payout_cents = 0
    assert pct.compute_driver_payout_cents(order_amount_cents=10_000) == 7000


def test_rate_card_from_dict_driver_payout_fields():
    from porterchain_pricing.rate_card import rate_card_from_dict

    card = rate_card_from_dict(
        {
            "driver_payout_mode": "percent",
            "driver_flat_per_delivery_cents": 900,
            "driver_minimum_payout_cents": 100,
            "driver_share_pct": 65,
        }
    )
    assert card.driver_payout_mode == "percent"
    assert card.driver_flat_per_delivery_cents == 900
    assert card.compute_driver_payout_cents(order_amount_cents=2000) == 1300
