"""Ravi 2026-11-03: admin custom price can be a flat $ per parcel, any size (Wintergreen $9)."""

from __future__ import annotations

from porterchain_pricing import GeoPoint, PricingRequest
from porterchain_pricing.standard_card import OrgPricing

from porterchain_api.pricing_engine.smart_apply import _org_custom, three_model_preview


def _req(**kw):
    return PricingRequest(pickup=GeoPoint(lat=43.65, lng=-79.38), dropoff=GeoPoint(lat=43.7, lng=-79.4),
                          vehicle_class="cargo_van", channel="merchant", **kw)


ORG = OrgPricing(mode="custom", flat_parcel_cents=900)


def test_flat_price_ignores_size_and_handling():
    small = _org_custom(_req(weight_kg=4, dimensions={"length": 40, "width": 30, "height": 20}), ORG, "o")
    heavy = _org_custom(_req(weight_kg=52, dimensions={"length": 70, "width": 45, "height": 40}), ORG, "o")
    assert small.subtotal_cents == 900 and heavy.subtotal_cents == 900
    assert small.metadata["price_rule"] == "custom_flat_parcel"
    assert [i.code for i in heavy.items] == ["custom_flat_parcel"]


def test_flat_price_does_not_touch_hourly_vehicle():
    std = three_model_preview(OrgPricing())
    cus = three_model_preview(ORG)
    by = {r["sample"]: r for r in cus}
    assert by["small_parcel_(fits_20x14x14_in)"]["custom_cents"] == 900
    assert by["handling_+30_(101-125_lb)"]["custom_cents"] == 900
    assert by["cargo_van_3_h"]["custom_cents"] == {r["sample"]: r for r in std}["cargo_van_3_h"]["standard_cents"]


def test_117_parcels_at_9_dollars_is_1053_before_hst():
    total = sum(_org_custom(_req(weight_kg=3, dimensions={"length": 30, "width": 20, "height": 10}), ORG, "o").subtotal_cents
                for _ in range(117))
    assert total == 105300 and round(total * 0.13) == 13689
