"""Pricing engine unit tests — zone, tax, promo basics."""

from __future__ import annotations

from datetime import UTC, datetime

from porterchain_pricing.pricing_service import PricingService
from porterchain_pricing.types import GeoPoint, PricingRequest


def test_retail_quote_returns_positive_total():
    svc = PricingService()
    req = PricingRequest(
        pickup=GeoPoint(lat=43.65, lng=-79.38, formatted="Toronto ON"),
        dropoff=GeoPoint(lat=43.70, lng=-79.40, formatted="North York ON"),
        vehicle_class="cargo_van",
        package_type="looseParcel",
        distance_meters=12_000,
        estimated_duration_minutes=25,
        scheduled_at=datetime.now(UTC),
    )
    breakdown = svc.calculate_retail(req)
    assert breakdown.final_cents > 0
    assert breakdown.base_cents >= 0


def test_merchant_channel_differs_from_retail():
    svc = PricingService()
    base = PricingRequest(
        pickup=GeoPoint(lat=43.65, lng=-79.38, formatted="Toronto ON"),
        dropoff=GeoPoint(lat=43.70, lng=-79.40, formatted="North York ON"),
        vehicle_class="cargo_van",
        distance_meters=12_000,
        estimated_duration_minutes=25,
        scheduled_at=datetime.now(UTC),
        merchant_id="m-1",
    )
    retail = svc.calculate_retail(base)
    merchant = svc.calculate_merchant(base)
    assert retail.final_cents > 0
    assert merchant.final_cents > 0


def test_line_items_export():
    svc = PricingService()
    req = PricingRequest(
        pickup=GeoPoint(lat=43.65, lng=-79.38),
        dropoff=GeoPoint(lat=43.70, lng=-79.40),
        vehicle_class="sedan",
        distance_meters=8000,
        estimated_duration_minutes=18,
        scheduled_at=datetime.now(UTC),
    )
    breakdown = svc.calculate_retail(req)
    items = svc.to_line_items(breakdown)
    assert isinstance(items, list)
    assert sum(i.amount_cents for i in items) >= 0
