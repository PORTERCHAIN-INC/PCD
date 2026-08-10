"""Rate card helpers + GTA retail quote path."""

from __future__ import annotations

from datetime import UTC, datetime

from porterchain_pricing.engine import PricingEngine
from porterchain_pricing.rate_card import RateCard, default_rate_card, merge_merchant_overlay, rate_card_from_dict
from porterchain_pricing.types import GeoPoint, PricingContext, PricingRequest


def _req(**kwargs) -> PricingRequest:
    base = dict(
        pickup=GeoPoint(lat=43.65, lng=-79.38, formatted="Toronto"),
        dropoff=GeoPoint(lat=43.70, lng=-79.40, formatted="North York"),
        vehicle_class="cargoVan",
        distance_meters=10_000,
        estimated_duration_minutes=20,
        scheduled_at=datetime(2026, 7, 13, 12, 0, tzinfo=UTC),  # Monday
        is_downtown=False,
        is_upper_zone=False,
    )
    base.update(kwargs)
    return PricingRequest(**base)


def test_default_rate_card_matches_catalog_floor():
    card = default_rate_card()
    assert card.vehicle("sedan").per_km_cents == 100
    assert card.liftgate_cents == 4500


def test_retail_uses_gta_matrix_not_rate_card_per_km():
    """Retail quotes ignore legacy per-km rate card — GTA matrix is authoritative."""
    card = default_rate_card()
    card.vehicles["cargoVan"] = card.vehicles.get("cargoVan") or card.vehicle("cargoVan")
    engine = PricingEngine()
    breakdown = engine.calculate(_req(channel="retail", vehicle_class="cargoVan"), PricingContext(rate_card=card))
    # cargo_van base $65 for 10 km, 1 drop
    assert breakdown.final_cents == 6500
    assert breakdown.metadata.get("pricing_model") == "gta_delivery_rate"
    assert breakdown.metadata.get("gta_vehicle_type") == "cargo_van"


def test_merge_merchant_overlay_still_builds_card():
    system = default_rate_card()
    effective = merge_merchant_overlay(
        system,
        {"rate_card": {"vehicles": {"cargoVan": {"per_km_cents": 100, "minimum_cents": 5000, "surcharge_cents": 0}}}},
    )
    assert effective.vehicle("cargoVan").minimum_cents == 5000


def test_extra_drop_from_additional_stops():
    engine = PricingEngine()
    breakdown = engine.calculate(
        _req(
            vehicle_class="sedan",
            additional_stops=[GeoPoint(lat=43.68, lng=-79.39)],
            is_downtown=False,
            is_upper_zone=False,
        ),
        PricingContext(),
    )
    # sedan $45 + 1 extra drop $15 = $60
    assert breakdown.final_cents == 6000
    assert any(i.code == "stop_fees" for i in breakdown.items)


def test_share_pct_in_metadata():
    card = RateCard(driver_share_pct=70, platform_share_pct=30)
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
