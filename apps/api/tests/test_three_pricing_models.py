"""Ravi 2026-10-31: parcel $6/$9 + size/weight table, vehicle hourly (merchants), admin custom."""

import pytest

from porterchain_pricing.three_models import handling_tier, hourly_price, parcel_price
from porterchain_pricing.types import GeoPoint, ParcelSpec, PricingRequest

IN = 2.54
LB = 1 / 2.20462


def req(parcels=(), **kw):
    base = dict(pickup=GeoPoint(lat=43.65, lng=-79.38), dropoff=GeoPoint(lat=43.7, lng=-79.4), vehicle_class="cargo_van")
    base.update(kw)
    return PricingRequest(parcels=[ParcelSpec(weight_kg=w, dimensions=d) for w, d in parcels], **base)


def d(l, w, h):
    return {"length": l * IN, "width": w * IN, "height": h * IN}


@pytest.mark.parametrize(
    "lb,dims,expect",
    [
        (5, d(20, 14, 14), 600),        # exactly fits small
        (5, d(21, 14, 14), 900),        # one inch over: van parcel
        (5, d(14, 20, 14), 600),        # orientation does not matter
        (100, d(70, 45, 30), 900),      # standard van limit
        (101, d(30, 20, 20), 3900),     # tier 1 by weight
        (80, d(85, 45, 20), 6900),      # Kaylulu A: size tier 2
        (130, d(70, 45, 20), 6900),     # Kaylulu B: weight tier 2
        (110, d(85, 45, 20), 6900),     # Kaylulu C: both, higher wins, no stacking
        (150, d(90, 50, 20), 6900),     # tier 2 limit
        (5, None, 600),                 # no size: small
    ],
)
def test_parcel_table(lb, dims, expect):
    bd = parcel_price(req([(lb * LB, dims)]))
    assert bd.subtotal_cents == expect


@pytest.mark.parametrize("lb,dims", [(151, d(10, 10, 10)), (10, d(91, 40, 20)), (10, d(80, 51, 20))])
def test_over_tier2_is_custom_quote(lb, dims):
    bd = parcel_price(req([(lb * LB, dims)]))
    assert bd.metadata["custom_quote"] and bd.subtotal_cents == 0


def test_mixed_parcels_sum():
    bd = parcel_price(req([(2, d(10, 10, 5)), (2, d(10, 10, 5)), (20, d(30, 20, 20)), (55, d(40, 20, 20))]))
    # 2 small + 2 van ($18) + one tier-1 by weight (121 lb) +$30
    assert bd.subtotal_cents == 2 * 600 + 2 * 900 + 3000


def test_parcel_count_without_parcels():
    r = PricingRequest(pickup=GeoPoint(lat=1, lng=1), dropoff=GeoPoint(lat=1, lng=1), vehicle_class="sedan_suv", parcel_count=3)
    assert parcel_price(r).subtotal_cents == 1800


def test_handling_tier_labels():
    assert handling_tier(None, None)[0] == 0


@pytest.mark.parametrize(
    "vc,mins,hours,help_,expect",
    [
        ("sedan_suv", 60, None, 0, 12000),      # 3 h minimum x $40
        ("pickup", 60, None, 0, 12000),
        ("cargo_van", 200, None, 0, 21000),     # 200 min = 3.33 h -> 3.5 h (15-min steps) x $60
        ("sprinter_van", None, 4, 0, 24000),
        ("box_16", None, 5, 3, 35000 + 9000),   # 5 h x $70 + 3 help stops
        ("box_20", None, 2, 1, 21000 + 3000),
    ],
)
def test_hourly(vc, mins, hours, help_, expect):
    r = req(vehicle_class=vc, estimated_duration_minutes=mins, dedicated_hours=hours, help_stops=help_, booking_mode="vehicle")
    bd = hourly_price(r)
    assert bd.subtotal_cents == expect
