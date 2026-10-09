"""Kaylulu contract schedule (kaylulu-2026-09) — data counts and golden bills.

Every expected number below is copied from the signed schedule: A1/A2/A3 rates,
the A4 sample bills, the A2 compact examples and the A3 handling examples.
"""

from __future__ import annotations

import pytest

from porterchain_pricing.contract_schedule import (
    SCHEDULE_FILES,
    load_contract_schedule,
    raw_contract_schedule,
)
from porterchain_pricing.engine import PricingEngine
from porterchain_pricing.policy import policy_from_config
from porterchain_pricing.types import (
    FsaRateRecord,
    GeoPoint,
    ParcelSpec,
    PricingContext,
    PricingRequest,
    TaxConfig,
    ZoneRecord,
)

SCHEDULE_ID = "kaylulu-2026-09"
MID = "kaylulu"
IN = 2.54
LB = 0.45359237
SMALL = {"length": 8 * IN, "width": 8 * IN, "height": 8 * IN}  # fits compact + van grouping
MEDIUM = {"length": 20 * IN, "width": 20 * IN, "height": 20 * IN}  # van, one stop per parcel
HAMILTON = {"L8B", "L8E", "L8G", "L8H", "L8J", "L8K", "L8L", "L8M", "L8N", "L8P", "L8R"}
HAMILTON |= {"L8S", "L8T", "L8V", "L8W", "L9A", "L9B", "L9C", "L9G", "L9H", "L9K"}
REGISTRY_GAPS = ("L5P", "M7R", "M7A", "M7Y", "L3E", "L3J", "L3W", "N6H", "N6J", "N6K")


def _schedule():
    terms = load_contract_schedule(SCHEDULE_ID)
    assert terms is not None
    return terms


def _ctx(**extra) -> PricingContext:
    config = {
        "pricing_model": "fsa",
        "surcharges": {"downtown": False, "upper_zone": False},
        "schedule": {"fsa_miss": "refuse", "fuel_surcharge_percent": 0, "contract_schedule": SCHEDULE_ID},
    }
    return PricingContext(merchant_policy=policy_from_config(config), **extra)


def _point(fsa: str) -> GeoPoint:
    return GeoPoint(lat=43.6, lng=-79.6, formatted=f"{fsa} 1A1, ON", postal=f"{fsa} 1A1")


def _price(fsas, *, vehicle="cargo_van", parcels=None, parcel_count=None, ctx=None, **kw):
    request = PricingRequest(
        pickup=_point("L9T"),
        dropoff=_point(fsas[0]),
        additional_stops=[_point(f) for f in fsas[1:]],
        vehicle_class=vehicle,
        channel="merchant",
        merchant_id=MID,
        parcels=list(parcels or []),
        parcel_count=parcel_count or max(len(parcels or []), len(fsas)),
        distance_meters=50_000,
        **kw,
    )
    return PricingEngine().calculate(request, ctx or _ctx())


# ── data ────────────────────────────────────────────────────────────────


def test_schedule_file_counts_match_the_contract():
    terms = _schedule()
    counts = {t.code: len(t.fsas) for t in terms.van_tiers}
    assert counts == {"T1": 187, "T2": 97, "T3": 37}
    assert len(terms.custom_quote_fsas) == 17
    assert len(terms.compact.fsas) == 117
    assert SCHEDULE_FILES[SCHEDULE_ID].endswith(".json")


def test_schedule_tiers_are_disjoint_and_compact_is_d1_plus_hamilton():
    terms = _schedule()
    t1, t2, t3 = (t.fsas for t in terms.van_tiers)
    assert not (t1 & t2 or t1 & t3 or t2 & t3)
    assert not ((t1 | t2 | t3) & terms.custom_quote_fsas)
    assert terms.compact.fsas - t1 == HAMILTON
    assert HAMILTON <= t2
    assert not any(code[1] == "0" for code in t1 | t2 | t3)


def test_schedule_rates_minimums_and_pickup():
    terms = _schedule()
    assert [(t.code, t.stop_cents, t.route_minimum_cents) for t in terms.van_tiers] == [
        ("T1", 3000, 12000),
        ("T2", 4500, 20000),
        ("T3", 6000, 25000),
    ]
    assert terms.pickup_cents == 4000
    assert terms.group_parcels_per_stop == 3
    assert terms.compact.route_minimum_cents == 5000
    assert [(b.max_stops, b.stop_cents, b.pickup_cents) for b in terms.compact.bands] == [
        (4, 1000, 1000),
        (None, 600, 0),
    ]
    assert [h.surcharge_cents for h in terms.handling] == [0, 3000, 6000]
    raw = raw_contract_schedule(SCHEDULE_ID)
    assert raw["custom_quote_fsas"] == sorted(raw["custom_quote_fsas"])


@pytest.mark.parametrize("fsa", REGISTRY_GAPS)
def test_registry_gap_fsas_are_covered_by_the_contract(fsa):
    terms = _schedule()
    assert fsa in terms.coverage_fsas()
    assert terms.van_tier(fsa) is not None
    assert _price([fsa]).final_cents > 0


def test_rural_unlisted_and_d4_are_custom_quotes():
    terms = _schedule()
    for fsa in ("L0A", "N0B", "K9J", "N7G", "K1A"):
        assert terms.van_tier(fsa) is None


# ── A4 sample bills (pre-tax) ───────────────────────────────────────────


@pytest.mark.parametrize(
    ("fsas", "expected"),
    [
        (["L5M", "M5V"], 12000),
        (["L8P", "N2G", "N1H"], 20000),
        (["L5M", "L6Y", "L8P", "N2G"], 20000),
        (["L5M", "L8P", "N2G", "N1P", "L3X"], 25000),
        (["L5M", "M5V", "N6A"], 25000),
    ],
)
def test_sample_bills_01_to_05(fsas, expected):
    b = _price(fsas)
    assert b.subtotal_cents == expected
    assert b.metadata["pricing_model"] == "contract_route"


def test_sample_bill_06_handling_tier_2_on_one_stop():
    heavy = ParcelSpec(stop_index=1, weight_kg=130 * LB, dimensions={"length": 70 * IN, "width": 45 * IN})
    b = _price(["N6A", "L4M", "N5A"], parcels=[ParcelSpec(0), heavy, ParcelSpec(2)])
    assert b.subtotal_cents == 28000
    assert b.metadata["true_bill_cents"] == 28000
    assert sum(i.amount_cents for i in b.items if i.code == "handling") == 6000


def test_sample_bills_with_hst_and_fuel_zero():
    b = _price(["L5M", "M5V"], ctx=_ctx(tax=TaxConfig(hst_percent=13.0)))
    assert b.subtotal_cents == 12000
    assert b.tax_cents == 1560


def test_five_parcel_t2_route_is_pickup_plus_five_stops():
    b = _price(["L8P"], parcels=[ParcelSpec(0, 5.0, MEDIUM)] * 5)
    assert b.subtotal_cents == 4000 + 5 * 4500 == 26500


def test_route_minimum_is_the_highest_tier_regardless_of_order():
    assert _price(["N6A", "L5M"]).subtotal_cents == 25000
    assert _price(["L5M", "N6A"]).subtotal_cents == 25000


def test_whole_route_refused_when_any_stop_is_d4_in_either_order():
    for fsas in (["L5M", "K9J"], ["K9J", "L5M"]):
        b = _price(fsas)
        assert b.metadata["fsa_refused"] is True
        assert b.metadata["custom_quote"] is True
        assert b.metadata["custom_quote_reason"] == "custom_quote_fsa"
        assert b.final_cents == 0


@pytest.mark.parametrize(("fsa", "reason"), [("L0A", "rural_fsa"), ("K1A", "unlisted_fsa")])
def test_rural_and_unlisted_stops_refuse_the_route(fsa, reason):
    b = _price(["L5M", fsa])
    assert b.metadata["custom_quote_reason"] == reason
    assert b.final_cents == 0


# ── A3 handling ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("weight_lb", "dims_in"),
    [
        (80, (85, 45)),  # A: size Tier 2, weight standard
        (130, (70, 45)),  # B: weight Tier 2, size standard
        (110, (85, 45)),  # C: weight Tier 1, size Tier 2 → higher
    ],
)
def test_handling_examples_a_b_c_charge_tier_2(weight_lb, dims_in):
    terms = _schedule()
    dims = (dims_in[0] * IN, dims_in[1] * IN, 10.0)
    assert terms.handling_tier(weight_lb * LB, dims).surcharge_cents == 6000


def test_handling_uses_the_two_longest_sides_in_any_order():
    terms = _schedule()
    assert terms.handling_tier(None, (45 * IN, 10.0, 85 * IN)).code == "handling_2"
    assert terms.handling_tier(None, (30 * IN, 75 * IN, 20 * IN)).code == "handling_1"


def test_handling_tier_1_adds_30_per_parcel():
    route = ["L8P", "N2G", "N1H", "N1P", "L3X"]  # 40 + 5×45 = 265, over the 200 minimum
    base = _price(route)
    heavy = [ParcelSpec(0, 110 * LB, MEDIUM)] + [ParcelSpec(i) for i in range(1, 5)]
    b = _price(route, parcels=heavy)
    assert base.subtotal_cents == 26500
    assert b.subtotal_cents == 26500 + 3000


def test_handling_tier_3_refuses_the_route():
    b = _price(["L5M", "M5V"], parcels=[ParcelSpec(0, 151 * LB, MEDIUM), ParcelSpec(1)])
    assert b.metadata["fsa_refused"] is True
    assert b.metadata["custom_quote_reason"] == "handling_beyond_schedule"
    b = _price(["L5M"], parcels=[ParcelSpec(0, 20.0, {"length": 95 * IN, "width": 40 * IN})])
    assert b.metadata["fsa_refused"] is True


def test_parcels_without_size_or_weight_are_standard():
    assert _price(["L5M", "M5V"], parcels=[ParcelSpec(0), ParcelSpec(1)]).subtotal_cents == 12000


# ── van stop grouping ───────────────────────────────────────────────────


def test_small_van_parcels_group_three_per_stop_at_one_destination():
    route = ["L8P", "N2G", "N1H", "N1P"]  # 40 + 4×45 = 220 base
    small = [ParcelSpec(0, 2.0, SMALL)] * 4 + [ParcelSpec(i) for i in range(1, 4)]
    # 4 small parcels at L8P → 2 stops; total 40 + 5×45 = 265
    assert _price(route, parcels=small).subtotal_cents == 26500


def test_handling_piece_is_never_grouped():
    route = ["L8P", "N2G", "N1H", "N1P"]
    parcels = [ParcelSpec(0, 2.0, SMALL)] * 2 + [ParcelSpec(0, 110 * LB, SMALL)]
    parcels += [ParcelSpec(i) for i in range(1, 4)]
    # L8P: 2 small grouped (1 stop) + 1 handling piece (own stop, +30) → 40 + 5×45 + 30
    assert _price(route, parcels=parcels).subtotal_cents == 29500


# ── A2 compact ──────────────────────────────────────────────────────────


def test_compact_examples():
    assert _price(["L5M"], vehicle="sedan_suv", parcels=[ParcelSpec(0, 1, SMALL)] * 3).subtotal_cents == 5000
    assert _price(["L5M"], vehicle="sedan_suv", parcels=[ParcelSpec(0, 1, SMALL)] * 6).subtotal_cents == 5000
    five = ["L5M", "L5N", "L5L", "L5B", "L5A"]
    parcels = [ParcelSpec(i, 1, SMALL) for i in range(5) for _ in range(3)]
    b = _price(five, vehicle="sedan_suv", parcels=parcels)
    assert b.subtotal_cents == 5000
    assert b.metadata["true_bill_cents"] == 3000
    assert _price(["L5M"], vehicle="sedan_suv", parcels=[ParcelSpec(0, 1, SMALL)] * 30).subtotal_cents == 6000


def test_compact_true_bill_and_no_handling_or_van_minimum():
    b = _price(["L5M"], vehicle="sedan_suv", parcels=[ParcelSpec(0, 1, SMALL)] * 3)
    assert b.metadata["contract_vehicle"] == "compact"
    assert b.metadata["true_bill_cents"] == 2000
    assert not [i for i in b.items if i.code in {"handling", "route_pickup", "contract_stop"}]


def test_compact_outside_territory_is_priced_as_van():
    b = _price(["N6A"], vehicle="sedan_suv", parcels=[ParcelSpec(0, 1, SMALL)])
    assert b.metadata["contract_vehicle"] == "cargo_van"
    assert b.metadata["compact_downgraded"] == "outside_compact_territory"
    assert b.subtotal_cents == 25000


def test_one_oversize_parcel_makes_the_whole_load_van():
    parcels = [ParcelSpec(0, 1, SMALL)] * 2 + [ParcelSpec(0, 1, {"length": 12 * IN, "width": 10 * IN})]
    b = _price(["L5M"], vehicle="sedan_suv", parcels=parcels)
    assert b.metadata["compact_downgraded"] == "parcel_over_compact_size"
    assert b.metadata["contract_vehicle"] == "cargo_van"
    assert b.subtotal_cents == 12000


def test_mixed_territory_route_is_all_van():
    parcels = [ParcelSpec(0, 1, SMALL), ParcelSpec(1, 1, SMALL)]
    b = _price(["L5M", "N6A"], vehicle="sedan_suv", parcels=parcels)
    assert b.metadata["contract_vehicle"] == "cargo_van"
    assert b.subtotal_cents == 25000


# ── leakage guards ──────────────────────────────────────────────────────


def _zone_x2() -> ZoneRecord:
    bounds = {"min_lat": 43.0, "max_lat": 44.5, "min_lng": -80.5, "max_lng": -78.5}
    return ZoneRecord(code="gta", name="GTA", bounds=bounds, multiplier=2.0)


def _generic_fsa_ctx(rows, **extra) -> PricingContext:
    config = {"pricing_model": "fsa", "schedule": {"fsa_miss": "refuse", "fuel_surcharge_percent": 0}}
    return PricingContext(merchant_policy=policy_from_config(config), fsa_rates=rows, **extra)


def test_contract_route_ignores_fsa_rows_zone_multiplier_and_stop_fees():
    rows = [
        FsaRateRecord(id="p1", dest_fsa="M5V", flat_cents=1),  # platform-wide row
        FsaRateRecord(id="m1", dest_fsa="M5V", flat_cents=99999, merchant_id=MID),
    ]
    b = _price(["L5M", "M5V"], ctx=_ctx(fsa_rates=rows, zones=[_zone_x2()]))
    assert b.subtotal_cents == 12000
    codes = {i.code for i in b.items}
    assert codes <= {"route_pickup", "contract_stop", "route_minimum", "handling"}


def test_without_parcels_parcel_count_lands_on_the_dropoff():
    b = _price(["L8P"], parcel_count=5, dimensions=MEDIUM, weight_kg=25.0)
    assert b.subtotal_cents == 26500


def test_unknown_schedule_id_falls_back_to_generic_fsa_path():
    config = {"pricing_model": "fsa", "schedule": {"fsa_miss": "refuse", "contract_schedule": "nope"}}
    b = _price(["L5M"], ctx=PricingContext(merchant_policy=policy_from_config(config)))
    assert b.metadata["contract_schedule_unknown"] == "nope"
    assert b.metadata["fsa_refused"] is True


def test_distance_merchant_with_schedule_key_is_unchanged():
    config = {"pricing_model": "distance", "schedule": {"contract_schedule": SCHEDULE_ID}}
    b = _price(["L5M"], ctx=PricingContext(merchant_policy=policy_from_config(config)))
    assert b.metadata["pricing_model"] == "gta_delivery_rate"


def test_generic_fsa_flat_rate_is_not_zone_multiplied():
    rows = [FsaRateRecord(id="m1", dest_fsa="L5M", flat_cents=3000, merchant_id=MID)]
    b = _price(["L5M"], ctx=_generic_fsa_ctx(rows, zones=[_zone_x2()]))
    assert b.metadata["pricing_model"] == "fsa_flat_rate"
    assert b.subtotal_cents == 3000
    assert "zone_multiplier" not in {i.code for i in b.items}


def test_generic_fsa_merchant_with_own_table_ignores_platform_rows():
    rows = [
        FsaRateRecord(id="m1", dest_fsa="L5M", flat_cents=3000, merchant_id=MID),
        FsaRateRecord(id="p1", dest_fsa="M5V", flat_cents=1500),  # platform-wide
    ]
    assert _price(["L5M"], ctx=_generic_fsa_ctx(rows)).subtotal_cents == 3000
    refused = _price(["M5V"], ctx=_generic_fsa_ctx(rows))
    assert refused.metadata["fsa_refused"] is True


def test_generic_fsa_merchant_without_own_rows_still_uses_platform_rows():
    rows = [FsaRateRecord(id="p1", dest_fsa="M5V", flat_cents=1500)]
    assert _price(["M5V"], ctx=_generic_fsa_ctx(rows)).subtotal_cents == 1500
