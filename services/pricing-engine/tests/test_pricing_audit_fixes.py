"""Regression tests for the Oct 2026 pricing audit fixes (engine side)."""

from __future__ import annotations

from porterchain_pricing.engine import PricingEngine
from porterchain_pricing.gta_rate import (
    DOWNTOWN_FSAS,
    is_downtown_point,
    is_upper_zone_point,
)
from porterchain_pricing.policy import (
    FSA_MISS_REFUSE,
    CompactSchedule,
    MerchantPricingPolicy,
    MerchantSchedule,
)
from porterchain_pricing.pricing_service import PricingService
from porterchain_pricing.types import (
    FsaRateRecord,
    GeoPoint,
    PricingContext,
    PricingRequest,
    TaxConfig,
    ZoneRecord,
)

PICKUP = GeoPoint(lat=43.5890, lng=-79.6441, formatted="Mississauga, ON", postal="L4W 5N5")
DROPOFF = GeoPoint(lat=43.6426, lng=-79.3871, formatted="Toronto, ON", postal="M5V 2T6")


def _merchant_request(**kw) -> PricingRequest:
    return PricingRequest(
        pickup=kw.pop("pickup", PICKUP),
        dropoff=kw.pop("dropoff", DROPOFF),
        vehicle_class=kw.pop("vehicle_class", "cargo_van"),
        channel="merchant",
        merchant_id="m1",
        distance_meters=kw.pop("distance_meters", 30_000),
        **kw,
    )


def _codes(b) -> list[str]:
    return [i.code for i in b.items]


# ---------------------------------------------------------------- bug 1


class _CapturingEngine(PricingEngine):
    def __init__(self) -> None:
        super().__init__()
        self.seen: PricingRequest | None = None

    def calculate(self, request, ctx=None):  # type: ignore[override]
        self.seen = request
        return super().calculate(request, ctx)


def test_calculate_merchant_preserves_every_request_field():
    svc = PricingService()
    svc.engine = _CapturingEngine()
    svc.calculate_merchant(_merchant_request(parcel_count=7, wait_minutes=12.0, requires_liftgate=True))
    seen = svc.engine.seen
    assert seen is not None
    assert seen.parcel_count == 7
    assert seen.wait_minutes == 12.0
    assert seen.requires_liftgate is True
    assert seen.channel == "merchant"


def test_calculate_retail_forces_retail_channel_and_drops_merchant():
    svc = PricingService()
    svc.engine = _CapturingEngine()
    svc.calculate_retail(_merchant_request(parcel_count=3))
    seen = svc.engine.seen
    assert seen is not None
    assert seen.channel == "retail"
    assert seen.merchant_id is None
    assert seen.parcel_count == 3


# ---------------------------------------------------------------- bug 2


def test_compact_banding_drops_stop_fees():
    policy = MerchantPricingPolicy(
        pricing_model="distance",
        schedule=MerchantSchedule(compact=CompactSchedule(enabled=True, route_minimum_cents=0)),
    )
    ctx = PricingContext(merchant_policy=policy, tax=TaxConfig(hst_percent=0.0))
    ctx.fsa_rates = [FsaRateRecord(id="t", dest_fsa="M5V", flat_cents=1500, vehicle_class="sedan_suv")]
    req = _merchant_request(vehicle_class="sedan_suv", total_pickups=2, total_drops=4, parcel_count=3)
    result = PricingEngine().calculate(req, ctx)
    assert result.metadata.get("compact_banding") is True
    assert "stop_fees" not in _codes(result)
    assert "compact_stop" in _codes(result)
    assert result.final_cents == 1000


# ---------------------------------------------------------------- bug 4


def test_downtown_is_the_downtown_fsa_set_not_a_latitude_box():
    assert "M5V" in DOWNTOWN_FSAS
    assert is_downtown_point(GeoPoint(lat=43.64, lng=-79.39, postal="M5V 2T6"))
    # Etobicoke / Mimico — south of Bloor, but not downtown.
    assert not is_downtown_point(GeoPoint(lat=43.60, lng=-79.50, postal="M8W 1A1"))
    # Coordinates alone (no postal / formatted FSA) never add the surcharge.
    assert not is_downtown_point(GeoPoint(lat=43.65, lng=-79.38))


def test_upper_zone_uses_fsa_or_whole_locality_not_substring():
    assert is_upper_zone_point(GeoPoint(lat=43.85, lng=-79.33, postal="L3R 0A1"))
    assert is_upper_zone_point(GeoPoint(lat=None, lng=None, formatted="5 Main St, Markham, ON"))
    assert is_upper_zone_point(GeoPoint(lat=None, lng=None, formatted="1 Yonge St, North York, ON"))
    assert not is_upper_zone_point(
        GeoPoint(lat=None, lng=None, formatted="1200 Markham Rd, Scarborough, ON M1H 2Y5")
    )
    assert not is_upper_zone_point(
        GeoPoint(lat=None, lng=None, formatted="600 Markham St, Toronto, ON M6G 2L8")
    )


# ---------------------------------------------------------------- bug 5 (engine side)


def test_fsa_refuse_finalizes_at_zero_with_flag():
    policy = MerchantPricingPolicy(pricing_model="fsa", schedule=MerchantSchedule(fsa_miss=FSA_MISS_REFUSE))
    ctx = PricingContext(merchant_policy=policy)
    ctx.fsa_rates = [FsaRateRecord(id="r", dest_fsa="K1A", flat_cents=1800)]
    result = PricingEngine().calculate(_merchant_request(), ctx)
    assert result.metadata.get("fsa_refused") is True
    assert result.final_cents == 0


# ---------------------------------------------------------------- bug 6


def test_volume_discount_applies_to_the_real_charges():
    ctx = PricingContext(
        merchant_pricing_config={"volume_discounts": [{"min_units": 1, "discount_percent": 10}]},
        tax=TaxConfig(hst_percent=0.0),
    )
    plain = PricingEngine().calculate(_merchant_request(), PricingContext(tax=TaxConfig(hst_percent=0.0)))
    discounted = PricingEngine().calculate(_merchant_request(), ctx)
    assert "volume_discount" in _codes(discounted)
    line = next(i for i in discounted.items if i.code == "volume_discount")
    assert line.amount_cents == -int(plain.final_cents * 0.10)
    assert discounted.final_cents == plain.final_cents + line.amount_cents


def test_volume_discount_is_merchant_only():
    ctx = PricingContext(merchant_pricing_config={"volume_discounts": [{"min_units": 1, "discount_percent": 10}]})
    req = PricingRequest(
        pickup=PICKUP, dropoff=DROPOFF, vehicle_class="cargo_van", channel="retail", distance_meters=30_000
    )
    assert "volume_discount" not in _codes(PricingEngine().calculate(req, ctx))


# ---------------------------------------------------------------- bug 7


def _zone(mult: float) -> ZoneRecord:
    return ZoneRecord(
        code="gta",
        name="GTA",
        bounds={"min_lat": 43.0, "max_lat": 44.5, "min_lng": -80.5, "max_lng": -78.5},
        multiplier=mult,
    )


def test_zone_multiplier_is_applied_as_its_own_line():
    base = PricingEngine().calculate(
        _merchant_request(), PricingContext(zones=[_zone(1.0)], tax=TaxConfig(hst_percent=0.0))
    )
    bumped = PricingEngine().calculate(
        _merchant_request(), PricingContext(zones=[_zone(1.2)], tax=TaxConfig(hst_percent=0.0))
    )
    assert "zone_multiplier" not in _codes(base)
    line = next(i for i in bumped.items if i.code == "zone_multiplier")
    assert line.amount_cents == round(base.final_cents * 0.2)
    assert bumped.final_cents == base.final_cents + line.amount_cents
    assert bumped.metadata["zone_multiplier_applied"] == 1.2


def test_default_zones_do_not_change_prices():
    result = PricingEngine().calculate(_merchant_request(), PricingContext())
    assert "zone_multiplier" not in _codes(result)


# ---------------------------------------------------------------- audit-v2


def test_zone_multiplier_skips_compact_banding():
    """Ravi: zone must not scale compact banding (all-in territory rates)."""
    policy = MerchantPricingPolicy(
        pricing_model="distance",
        schedule=MerchantSchedule(compact=CompactSchedule(enabled=True, route_minimum_cents=0)),
    )
    ctx = PricingContext(
        merchant_policy=policy,
        tax=TaxConfig(hst_percent=0.0),
        zones=[_zone(1.2)],
        fsa_rates=[FsaRateRecord(id="t", dest_fsa="M5V", flat_cents=1500, vehicle_class="sedan_suv")],
    )
    req = _merchant_request(vehicle_class="sedan_suv", total_pickups=1, total_drops=1, parcel_count=3)
    result = PricingEngine().calculate(req, ctx)
    assert result.metadata.get("compact_banding") is True
    assert "zone_multiplier" not in _codes(result)
    assert next(i for i in result.items if i.code == "compact_stop").amount_cents == 1000
    assert result.final_cents == 1000


def test_downtown_fsas_exclude_m7a():
    assert "M7A" not in DOWNTOWN_FSAS
    assert is_downtown_point(GeoPoint(lat=43.65, lng=-79.38, formatted="x", postal="M5X 1A9"))
    assert not is_downtown_point(GeoPoint(lat=43.66, lng=-79.39, formatted="x", postal="M7A 1A1"))


def test_compact_defaults_match_named_constants():
    from porterchain_pricing.policy import (
        COMPACT_DEFAULT_BAND_FAR_CENTS,
        COMPACT_DEFAULT_BAND_NEAR_CENTS,
        COMPACT_DEFAULT_BAND_NEAR_MAX_STOPS,
        COMPACT_DEFAULT_PARCELS_PER_STOP,
        COMPACT_DEFAULT_ROUTE_MINIMUM_CENTS,
    )

    c = CompactSchedule()
    assert c.parcels_per_stop == COMPACT_DEFAULT_PARCELS_PER_STOP == 3
    assert c.route_minimum_cents == COMPACT_DEFAULT_ROUTE_MINIMUM_CENTS == 5000
    assert c.stop_rates[0].cents == COMPACT_DEFAULT_BAND_NEAR_CENTS == 1000
    assert c.stop_rates[0].max_stops == COMPACT_DEFAULT_BAND_NEAR_MAX_STOPS == 4
    assert c.stop_rates[1].cents == COMPACT_DEFAULT_BAND_FAR_CENTS == 600
