"""Liftgate pricing surcharge tests (§8.1.7)."""

from __future__ import annotations

from datetime import UTC, datetime

from porterchain_pricing.catalog import LIFTGATE_SURCHARGE_CENTS
from porterchain_pricing.pricing_service import PricingService
from porterchain_pricing.types import GeoPoint, PricingRequest


def test_liftgate_adds_line_item():
    svc = PricingService()
    base = PricingRequest(
        pickup=GeoPoint(lat=43.65, lng=-79.38, formatted="Toronto ON"),
        dropoff=GeoPoint(lat=43.70, lng=-79.40, formatted="North York ON"),
        vehicle_class="cargo_van",
        distance_meters=12_000,
        estimated_duration_minutes=25,
        scheduled_at=datetime.now(UTC),
        channel="merchant",
        merchant_id="m-1",
    )
    without = svc.calculate_merchant(base)
    with_liftgate = svc.calculate_merchant(
        PricingRequest(
            pickup=base.pickup,
            dropoff=base.dropoff,
            vehicle_class=base.vehicle_class,
            distance_meters=base.distance_meters,
            estimated_duration_minutes=base.estimated_duration_minutes,
            scheduled_at=base.scheduled_at,
            channel=base.channel,
            merchant_id=base.merchant_id,
            requires_liftgate=True,
        )
    )
    assert with_liftgate.subtotal_cents == without.subtotal_cents + LIFTGATE_SURCHARGE_CENTS
    assert with_liftgate.final_cents > without.final_cents
    codes = [item.code for item in with_liftgate.items]
    assert "liftgate" in codes
