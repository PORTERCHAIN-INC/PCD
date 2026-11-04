"""Ravi 2026-10-31: per-vehicle-class rates (proposal §5) for merchant and admin quotes."""

from porterchain_pricing.types import GeoPoint, PriceBreakdown, PriceLineItem, PricingRequest
from porterchain_pricing.vehicle_class_rate import class_rate_cents

from porterchain_api.pricing_engine.smart_apply import apply_vehicle_class_rate


def _req(vc: str, km: float, **kw) -> PricingRequest:
    return PricingRequest(pickup=GeoPoint(lat=43.65, lng=-79.38, formatted="a"),
                          dropoff=GeoPoint(lat=43.7, lng=-79.4, formatted="b", postal="M4W 1A1"),
                          vehicle_class=vc, distance_meters=int(km * 1000), channel="merchant", **kw)


def _std(sub: int) -> PriceBreakdown:
    bd = PriceBreakdown(items=[PriceLineItem("band:S", "Small", sub)], metadata={"pricing": "standard_card"})
    bd.subtotal_cents = bd.base_cents = sub
    bd.tax_cents = int((sub * 13 + 50) // 100)
    bd.final_cents = sub + bd.tax_cents
    return bd


def test_table():
    assert class_rate_cents("sedan_suv", 4) == 2500
    assert class_rate_cents("cargo_van", 10) == 5500
    assert class_rate_cents("cargo_van", 20) == 7500
    assert class_rate_cents("box_20", 12) == 15700
    assert class_rate_cents("pickup", 0) == 4500
    assert class_rate_cents("unknown", 5) is None


def test_small_parcel_minimum_six_even_with_cargo_van_default():
    bd = apply_vehicle_class_rate(_req("cargo_van", 20, dimensions="50x35x35"), _std(400))
    assert bd.subtotal_cents == 600 and bd.final_cents == 678
    assert bd.items[-1].code == "parcel_minimum" and bd.metadata["price_rule"] == "small_parcel_minimum"


def test_small_parcel_card_above_minimum_kept():
    bd = apply_vehicle_class_rate(_req("cargo_van", 20, dimensions="30x20x10"), _std(1620))
    assert bd.final_cents == 1620 + 211 and bd.metadata["price_rule"] == "parcel_card"


def test_21_inch_parcel_is_van_minimum():
    bd = apply_vehicle_class_rate(_req("sedan_suv", 5, dimensions="53.34x30x30"), _std(500))
    assert bd.subtotal_cents == 900 and bd.metadata["parcel_size_class"] == "van"


def test_orientation_largest_side_decides():
    from porterchain_pricing.vehicle_class_rate import _fits_small

    assert _fits_small("35x50x35")  # 14 x 20 x 14 in any order
    assert not _fits_small("40x40x40")  # 15.7 in on two sides > 14
    assert _fits_small(None)


def test_no_postal_legacy_gets_minimum():
    bd = PriceBreakdown(items=[PriceLineItem("base", "Base", 500)], metadata={})
    bd.subtotal_cents, bd.tax_cents, bd.final_cents = 500, 65, 565
    bd = apply_vehicle_class_rate(_req("cargo_van", 5), bd)
    assert bd.final_cents == 600 + 78


def test_vehicle_mode_manual_and_contract_untouched():
    bd = apply_vehicle_class_rate(_req("cargo_van", 20, booking_mode="vehicle"), _std(1000))
    assert bd.final_cents == 1130
    m = PriceBreakdown(metadata={"manual_quote": True, "fsa_refused": True})
    assert apply_vehicle_class_rate(_req("cargo_van", 20), m).final_cents == 0
    c = _std(1000); c.contract_id = "k1"
    assert apply_vehicle_class_rate(_req("cargo_van", 20), c).final_cents == 1130
    # large card price never lowered
    assert apply_vehicle_class_rate(_req("cargo_van", 20), _std(7000)).final_cents == 7910


def test_admin_stop_keeps_postal():
    from porterchain_api.admin_engine.order_builder_service import _normalize_stops, _stop_addr
    from porterchain_api.schemas_admin import AdminOrderStopInput

    stops = _normalize_stops([AdminOrderStopInput(type="pickup", sequence=0, formatted="1 A St", lat=1, lng=2, postal="M5V 2T6")])
    assert stops[0]["postal"] == "M5V 2T6" and _stop_addr(stops[0])["postal"] == "M5V 2T6"
