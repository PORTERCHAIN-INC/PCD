"""Price book (global settings + merchant overrides) — v3 §6.4 worked examples.

Contract merchants (Kaylulu) must not move when the book is switched on, and
the book's handling / small-parcel defaults must equal the signed contract.
"""

from __future__ import annotations

import pytest

from porterchain_pricing.contract_schedule import raw_contract_schedule
from porterchain_pricing.engine import PricingEngine
from porterchain_pricing.policy import policy_from_config
from porterchain_pricing.price_book import (
    PLACEHOLDER_PATHS,
    default_price_book,
    effective_price_book,
    normalize_price_book,
)
from porterchain_pricing.types import GeoPoint, ParcelSpec, PricingContext, PricingRequest, TaxConfig
from test_contract_schedule import IN, LB, MEDIUM, SMALL
from test_contract_schedule import _ctx as _kaylulu_ctx
from test_contract_schedule import _price as _kaylulu_price

STANDARD_BOX = {"length": 40 * IN, "width": 30 * IN, "height": 20 * IN}  # sofa box, not small


def _point(fsa: str) -> GeoPoint:
    return GeoPoint(lat=43.6, lng=-79.6, formatted=f"{fsa} 1A1, ON", postal=f"{fsa} 1A1")


def _ctx(*, model="fsa", book=None, merchant_book=None, **extra) -> PricingContext:
    config = {
        "pricing_model": model,
        "surcharges": {"downtown": False, "upper_zone": False},
        "schedule": {"fsa_miss": "refuse", "fuel_surcharge_percent": 0},
        "price_book": {"enabled": True, **(merchant_book or {})},
    }
    return PricingContext(
        merchant_policy=policy_from_config(config),
        merchant_pricing_config=config,
        price_book=book,
        **extra,
    )


def _price(parcels, *, ctx=None, fsas=("L5M",), vehicle="cargo_van", **kw):
    request = PricingRequest(
        pickup=_point("L9T"),
        dropoff=_point(fsas[0]),
        additional_stops=[_point(f) for f in fsas[1:]],
        vehicle_class=vehicle,
        channel="merchant",
        merchant_id="m1",
        parcels=list(parcels),
        parcel_count=max(len(parcels), 1),
        distance_meters=10_000,
        **kw,
    )
    return PricingEngine().calculate(request, ctx or _ctx())


def _before_min(**kw) -> PricingContext:
    return _ctx(merchant_book={"minimum": {"cents": 0}, **kw})


def _sofa(item="sofa-1"):
    return [ParcelSpec(0, 50 * LB, STANDARD_BOX, item_key=item) for _ in range(3)]


# ── defaults ────────────────────────────────────────────────────────────


def test_defaults_are_off_and_validate():
    book = normalize_price_book(None)
    assert book == normalize_price_book(default_price_book())
    assert book["merchant_parcels"]["enabled"] is False
    assert book["retail"]["enabled"] is False
    assert book["dedicated"]["enabled"] is False
    assert book["multi_box_as_one_item"] is False
    assert "stop_price_cents" in PLACEHOLDER_PATHS


def test_handling_and_small_defaults_equal_the_kaylulu_contract():
    raw = raw_contract_schedule("kaylulu-2026-09")
    book = default_price_book()
    assert book["handling"] == raw["handling"]
    assert book["small_parcel"]["van_max_in"] == raw["van"]["grouping"]["max_packed_inches"]
    assert book["small_parcel"]["group_size"] == raw["van"]["grouping"]["parcels_per_stop"]
    assert book["small_parcel"]["compact_max_in"] == raw["compact"]["max_packed_inches"]


def test_invalid_books_are_rejected():
    with pytest.raises(ValueError, match="parcel_tiers"):
        normalize_price_book({"parcel_tiers": [{"max_parcels": 5, "cents_per_parcel": 400}]})
    with pytest.raises(ValueError, match="stop_price_cents"):
        normalize_price_book({"stop_price_cents": -1})
    with pytest.raises(ValueError, match="small_parcel.charge_mode"):
        normalize_price_book({"small_parcel": {"charge_mode": "half"}})
    with pytest.raises(ValueError, match="dedicated.unit"):
        normalize_price_book({"dedicated": {"unit": "week"}})


def test_merchant_overrides_sit_on_top_of_global():
    book = effective_price_book(
        {"stop_price_cents": 2500},
        {"price_book": {"enabled": True, "multi_box_as_one_item": True, "retail": {"enabled": True}}},
    )
    assert book["stop_price_cents"] == 2500
    assert book["merchant_parcels"]["enabled"] is True
    assert book["multi_box_as_one_item"] is True
    assert book["retail"]["enabled"] is False  # retail is global-only


# ── quotes unchanged while OFF ──────────────────────────────────────────


def test_book_off_leaves_existing_quote_untouched():
    cfg = {"pricing_model": "distance", "schedule": {"fuel_surcharge_percent": 0}}
    ctx_plain = PricingContext(merchant_policy=policy_from_config(cfg), merchant_pricing_config=cfg)
    ctx_book = PricingContext(
        merchant_policy=policy_from_config(cfg), merchant_pricing_config=cfg, price_book=default_price_book()
    )
    a = _price(_sofa(), ctx=ctx_plain)
    b = _price(_sofa(), ctx=ctx_book)
    assert [(i.code, i.amount_cents) for i in a.items] == [(i.code, i.amount_cents) for i in b.items]
    assert "price_book" not in b.metadata


def test_price_version_is_stamped_on_every_quote():
    b = _price([], ctx=_ctx(price_version="pv-7"))
    assert b.metadata["price_version"] == "pv-7"
    refused = _price([ParcelSpec(0, 200 * LB, STANDARD_BOX)], ctx=_ctx(price_version="pv-7"))
    assert refused.metadata["fsa_refused"] is True
    assert refused.metadata["price_version"] == "pv-7"


# ── v3 §6.4 non-contract examples (EXAMPLE values = defaults) ───────────


def test_one_stop_five_small_parcels_is_stop_price_then_route_minimum():
    b = _price([ParcelSpec(0, 1, SMALL)] * 5, ctx=_before_min())
    assert b.subtotal_cents == 2000
    b = _price([ParcelSpec(0, 1, SMALL)] * 5)
    assert b.subtotal_cents == 6000
    assert [i.code for i in b.items] == ["stop_price", "route_minimum"]


def test_three_box_sofa_multi_box_off():
    b = _price(_sofa(), ctx=_before_min())
    assert b.subtotal_cents == 2000 + 3 * 400
    assert b.metadata["price_book"]["billable_units"] == 3


def test_three_box_sofa_multi_box_on():
    b = _price(_sofa(), ctx=_before_min(multi_box_as_one_item=True))
    assert b.subtotal_cents == 2000 + 400
    assert b.metadata["price_book"]["billable_units"] == 1


def test_multi_box_two_items_are_two_units_and_handling_stays_per_box():
    boxes = _sofa("sofa-1") + [
        ParcelSpec(0, 110 * LB, STANDARD_BOX, item_key="table-1"),
        ParcelSpec(0, 110 * LB, STANDARD_BOX, item_key="table-1"),
    ]
    b = _price(boxes, ctx=_before_min(multi_box_as_one_item=True))
    assert b.metadata["price_book"]["billable_units"] == 2
    assert sum(i.amount_cents for i in b.items if i.code == "handling") == 2 * 3000
    assert b.subtotal_cents == 2000 + 2 * 400 + 6000


def test_twelve_parcels_eight_small_four_standard():
    parcels = [ParcelSpec(0, 1, SMALL)] * 8 + [ParcelSpec(0, 5, MEDIUM)] * 4
    b = _price(parcels, ctx=_before_min())
    assert b.subtotal_cents == 2000 + 4 * 400


def test_twelve_standard_parcels_use_the_11_to_20_tier():
    b = _price([ParcelSpec(0, 5, MEDIUM)] * 12, ctx=_before_min())
    assert b.subtotal_cents == 2000 + 12 * 300


def test_six_parcels_use_the_6_to_10_tier():
    b = _price([ParcelSpec(0, 5, MEDIUM)] * 6, ctx=_before_min())
    assert b.subtotal_cents == 2000 + 6 * 350


def test_over_twenty_parcels_is_a_custom_quote():
    b = _price([ParcelSpec(0, 5, MEDIUM)] * 21)
    assert b.metadata["fsa_refused"] is True
    assert b.metadata["custom_quote_reason"] == "parcel_quantity_custom_quote"
    assert b.final_cents == 0


def test_handling_tier_beyond_last_is_a_custom_quote():
    b = _price([ParcelSpec(0, 151 * LB, STANDARD_BOX)])
    assert b.metadata["custom_quote_reason"] == "handling_beyond_last_tier"


def test_small_per_group_mode_bills_one_unit_per_three():
    b = _price([ParcelSpec(0, 1, SMALL)] * 7, ctx=_before_min(small_parcel={"charge_mode": "per_group"}))
    assert b.subtotal_cents == 2000 + 3 * 400


def test_small_threshold_is_per_vehicle_class():
    eleven = {"length": 11 * IN, "width": 11 * IN, "height": 4 * IN}
    van = _price([ParcelSpec(0, 1, eleven)] * 2, ctx=_before_min())
    car = _price([ParcelSpec(0, 1, eleven)] * 2, ctx=_before_min(), vehicle="sedan_suv")
    assert van.subtotal_cents == 2000  # ≤ 12"×12" free in a van
    assert car.subtotal_cents == 2000 + 2 * 400  # over 10"×10" in a car


def test_fsa_row_still_sets_the_stop_price():
    from porterchain_pricing.types import FsaRateRecord

    ctx = _before_min()
    ctx.fsa_rates = [FsaRateRecord(id="r1", dest_fsa="L5M", flat_cents=3300)]
    b = _price(_sofa(), ctx=ctx)
    assert b.subtotal_cents == 3300 + 3 * 400


def test_distance_model_adds_parcel_tiers_to_the_distance_card():
    plain = _price([], ctx=_ctx(model="distance", merchant_book={"enabled": False}))
    b = _price(_sofa(), ctx=_ctx(model="distance", merchant_book={"minimum": {"cents": 0}}))
    assert b.subtotal_cents == plain.subtotal_cents + 3 * 400


def test_per_stop_minimum_mode():
    b = _price([], fsas=("L5M", "L5N"), ctx=_ctx(merchant_book={"minimum": {"cents": 3000, "mode": "per_stop"}}))
    assert b.subtotal_cents == 6000


def test_tax_applies_on_top():
    b = _price(_sofa(), ctx=_before_min(), **{})
    ctx = _before_min()
    ctx.tax = TaxConfig(hst_percent=13.0)
    t = _price(_sofa(), ctx=ctx)
    assert t.tax_cents == int(b.subtotal_cents * 0.13)


# ── retail fixed + dedicated vehicles ───────────────────────────────────


def _retail(book, **kw):
    request = PricingRequest(
        pickup=_point("L9T"), dropoff=_point("M5V"), vehicle_class="sedan_suv", distance_meters=30_000, **kw
    )
    return PricingEngine().calculate(request, PricingContext(price_book=book))


def test_retail_fixed_price_when_enabled():
    off = _retail(None)
    assert off.metadata.get("pricing_model") != "retail_fixed"
    on = _retail({"retail": {"enabled": True, "fixed_price_cents": 3900}})
    assert [(i.code, i.amount_cents) for i in on.items] == [("retail_fixed", 3900)]
    extra = _retail({"retail": {"enabled": True, "fixed_price_cents": 3900}}, parcel_count=7)
    assert extra.subtotal_cents == 3900 + 2 * 500


def test_dedicated_vehicle_half_day_and_hourly():
    book = {"dedicated": {"enabled": True}}
    b = _retail(book, booking_mode="vehicle", dedicated_hours=6)
    assert b.metadata["pricing_model"] == "dedicated"
    assert b.subtotal_cents == 2 * 16000
    hourly = _retail({"dedicated": {"enabled": True, "unit": "hour"}}, booking_mode="vehicle", dedicated_hours=2.5)
    assert hourly.subtotal_cents == 3 * 4500
    minimum = _retail(book, booking_mode="vehicle")
    assert minimum.subtotal_cents == 16000


# ── Kaylulu contract wins over the book ─────────────────────────────────


def _kaylulu_with_book(**extra):
    ctx = _kaylulu_ctx(price_book={"merchant_parcels": {"enabled": True}, "retail": {"enabled": True}}, **extra)
    ctx.merchant_pricing_config = {"price_book": {"enabled": True, "multi_box_as_one_item": True}}
    return ctx


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
def test_kaylulu_sample_bills_unchanged_with_book_on(fsas, expected):
    b = _kaylulu_price(fsas, ctx=_kaylulu_with_book())
    assert b.subtotal_cents == expected
    assert b.metadata["pricing_model"] == "contract_route"


def test_kaylulu_sample_06_and_compact_unchanged_with_book_on():
    heavy = ParcelSpec(stop_index=1, weight_kg=130 * LB, dimensions={"length": 70 * IN, "width": 45 * IN})
    b = _kaylulu_price(["N6A", "L4M", "N5A"], parcels=[ParcelSpec(0), heavy, ParcelSpec(2)], ctx=_kaylulu_with_book())
    assert b.subtotal_cents == 28000
    c = _kaylulu_price(["L5M"], vehicle="sedan_suv", parcels=[ParcelSpec(0, 1, SMALL)] * 30, ctx=_kaylulu_with_book())
    assert c.subtotal_cents == 6000


def test_kaylulu_three_box_sofa_is_three_stops_even_if_multi_box_flag_set():
    b = _kaylulu_price(["L5M"], parcels=_sofa(), ctx=_kaylulu_with_book())
    assert b.subtotal_cents == 4000 + 3 * 3000


def test_kaylulu_twelve_mixed_parcels_current_reading_is_385():
    parcels = (
        [ParcelSpec(0, 1, SMALL)] * 8
        + [ParcelSpec(0, 5, MEDIUM)] * 3
        + [ParcelSpec(0, 110 * LB, STANDARD_BOX)]
    )
    b = _kaylulu_price(["L8P"], parcels=parcels, ctx=_kaylulu_with_book())
    assert b.subtotal_cents == 38500


def test_kaylulu_hst_sample_unchanged():
    b = _kaylulu_price(["L5M", "M5V"], ctx=_kaylulu_with_book(tax=TaxConfig(hst_percent=13.0)))
    assert (b.subtotal_cents, b.tax_cents) == (12000, 1560)
