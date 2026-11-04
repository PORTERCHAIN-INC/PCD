"""Doc 72: live checkout / quotes / Shopify rates price on the Standard card (+ org Custom)."""

from __future__ import annotations

import uuid

import pytest

import porterchain_api.main  # noqa: F401
from porterchain_api.merchant_engine.booking_validation import BookingValidationError, assert_not_fsa_refused
from porterchain_api.pricing_engine import get_pricing_service
from porterchain_api.pricing_engine.models import PricingOrgPricing
from porterchain_api.pricing_engine.standard_live import zone_for_fsa
from porterchain_pricing import GeoPoint, PricingRequest
from porterchain_pricing.standard_card import ManualQuoteRequired


def _req(postal: str, *, channel: str = "merchant", merchant_id: str | None = None, kg: float = 4) -> PricingRequest:
    return PricingRequest(
        pickup=GeoPoint(lat=43.65, lng=-79.38, postal="M5V 2T6"),
        dropoff=GeoPoint(lat=43.7, lng=-79.4, postal=postal),
        vehicle_class="cargo_van", weight_kg=kg,
        dimensions={"length": 40, "width": 30, "height": 20},
        channel=channel, merchant_id=merchant_id,
    )


def test_zones():
    assert zone_for_fsa("M5V") == "Z1"
    assert zone_for_fsa("L5B") == "Z2" and zone_for_fsa("L7L") == "Z2"
    assert zone_for_fsa("N2L") == "Z3"
    with pytest.raises(ManualQuoteRequired):
        zone_for_fsa("H2X")


def test_retail_and_merchant_use_parcel_model(db):
    """2026-10-31 (Ravi): the S/M/L/XL standard card is retired; default = $6 small / $9 van + HST."""
    svc = get_pricing_service(db)
    retail = svc.calculate_retail(_req("M4C 1A1", channel="retail"))
    assert retail.metadata["pricing"] == "parcel_v2"
    assert retail.subtotal_cents == 600 and retail.tax_cents == 78 and retail.final_cents == 678
    b2b = svc.calculate_merchant(_req("M4C 1A1", merchant_id=str(uuid.uuid4())))
    assert b2b.metadata["pricing"] == "parcel_v2" and b2b.subtotal_cents == 600
    z2 = svc.calculate_retail(_req("L5B 1M2", channel="retail"))
    assert z2.subtotal_cents == 600  # no zone extras any more


def test_custom_org_pricing_applies(db):
    """Model 3: an admin custom merchant price overrides the parcel/hourly models."""
    mid = str(uuid.uuid4())
    db.add(PricingOrgPricing(org_id=mid, mode="custom", preset_pct=-10))
    db.flush()
    bd = get_pricing_service(db).calculate_merchant(_req("M4C 1A1", merchant_id=mid))
    assert bd.metadata["pricing"] == "custom_org" and bd.metadata["org_id"] == mid
    assert bd.subtotal_cents == 540 and bd.tax_cents == 70  # $6 small parcel -10 %


def test_custom_org_per_stop_adjusts_parcel_and_hourly(db):
    import dataclasses

    mid = str(uuid.uuid4())
    db.add(PricingOrgPricing(org_id=mid, mode="custom", preset_per_stop_cents=-150))
    db.flush()
    svc = get_pricing_service(db)
    assert svc.calculate_merchant(_req("M4C 1A1", merchant_id=mid)).subtotal_cents == 450  # $6 - $1.50
    veh = dataclasses.replace(_req("M4C 1A1", merchant_id=mid), booking_mode="vehicle")
    assert svc.calculate_merchant(veh).subtotal_cents == 17850  # 3 h x $60 - $1.50


def test_over_handling_table_is_custom_quote_never_free(db):
    heavy = get_pricing_service(db).calculate_retail(_req("M4C 1A1", channel="retail", kg=300))
    assert heavy.final_cents == 0 and heavy.metadata.get("custom_quote")
    with pytest.raises(BookingValidationError):
        assert_not_fsa_refused(heavy)


def test_no_postal_keeps_previous_engine(db):
    req = PricingRequest(pickup=GeoPoint(lat=43.65, lng=-79.38), dropoff=GeoPoint(lat=43.7, lng=-79.4),
                         vehicle_class="cargo_van", weight_kg=4, channel="retail")
    assert get_pricing_service(db).calculate_retail(req).metadata.get("pricing") != "standard_card"


def test_whole_vehicle_is_hourly_for_merchants_parcel_for_customers(db):
    import dataclasses

    r = dataclasses.replace(_req("M1P 4P5", merchant_id=str(uuid.uuid4())), booking_mode="vehicle")
    assert get_pricing_service(db).calculate_merchant(r).subtotal_cents == 18000  # 3 h x $60
    c = dataclasses.replace(_req("M1P 4P5", channel="retail"), booking_mode="vehicle")
    assert get_pricing_service(db).calculate_retail(c).metadata["pricing"] == "parcel_v2"


def test_whole_vehicle_quote_carries_13pct_hst_like_standard_card(db):
    """Doc 72 §8: HST 13 % always on its own line — whole-vehicle too, not just parcel bands."""
    import dataclasses

    r = dataclasses.replace(_req("M1P 4P5", channel="retail"), booking_mode="vehicle", weight_kg=None, dimensions=None)
    bd = get_pricing_service(db).calculate_retail(r)
    assert bd.subtotal_cents > 0
    assert bd.tax_cents == (bd.subtotal_cents * 13 + 50) // 100
    assert bd.final_cents == bd.subtotal_cents + bd.tax_cents
    parcel = get_pricing_service(db).calculate_retail(_req("M1P 4P5", channel="retail"))
    assert parcel.tax_cents == (parcel.subtotal_cents * 13 + 50) // 100


def test_whole_vehicle_hst_honours_exempt_merchant_ids(db):
    """pricing_tax.exempt_merchant_ids exempts the vehicle path, like TaxCalculator does for legacy pricing."""
    import dataclasses
    import uuid

    from porterchain_api.admin_models import SystemConfig

    mid = str(uuid.uuid4())
    row = db.query(SystemConfig).filter(SystemConfig.key == "pricing_tax").first()
    if row is None:
        row = SystemConfig(key="pricing_tax", value={})
        db.add(row)
    row.value = {**(row.value or {}), "exempt_merchant_ids": [mid]}
    db.flush()
    base = dataclasses.replace(_req("M1P 4P5", channel="merchant"), booking_mode="vehicle", weight_kg=None, dimensions=None)
    exempt = get_pricing_service(db).calculate_merchant(dataclasses.replace(base, merchant_id=mid))
    assert exempt.subtotal_cents > 0 and exempt.tax_cents == 0
    assert exempt.final_cents == exempt.subtotal_cents
    other = get_pricing_service(db).calculate_merchant(dataclasses.replace(base, merchant_id=str(uuid.uuid4())))
    assert other.tax_cents == (other.subtotal_cents * 13 + 50) // 100
