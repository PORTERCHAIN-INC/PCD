"""Pricing engine unit tests (§2.1.5)."""

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


def test_pricing_line_items():
    svc = PricingService()
    req = PricingRequest(
        pickup=GeoPoint(lat=43.65, lng=-79.38),
        dropoff=GeoPoint(lat=43.70, lng=-79.40),
        vehicle_class="sedan",
        distance_meters=8000,
        estimated_duration_minutes=18,
        scheduled_at=datetime.now(UTC),
    )
    items = svc.to_line_items(svc.calculate_retail(req))
    assert isinstance(items, list)
