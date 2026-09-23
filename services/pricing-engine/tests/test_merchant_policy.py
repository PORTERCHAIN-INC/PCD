"""Per-merchant pricing policy: model switch, surcharge opt-outs, size tiers."""

import pytest

from porterchain_pricing.components import SizeWeightService
from porterchain_pricing.engine import PricingEngine
from porterchain_pricing.policy import (
    MerchantPricingPolicy,
    SizeTier,
    policy_from_config,
)
from porterchain_pricing.types import FsaRateRecord, GeoPoint, PricingContext, PricingRequest

PICKUP = GeoPoint(lat=43.5890, lng=-79.6441, formatted="Mississauga, ON", postal="L4W 5N5")
DROPOFF = GeoPoint(lat=43.6426, lng=-79.3871, formatted="Toronto, ON", postal="M5V 2T6")


def _request(**kw) -> PricingRequest:
    return PricingRequest(
        pickup=kw.pop("pickup", PICKUP),
        dropoff=kw.pop("dropoff", DROPOFF),
        vehicle_class=kw.pop("vehicle_class", "cargo_van"),
        channel=kw.pop("channel", "merchant"),
        merchant_id=kw.pop("merchant_id", "m1"),
        **kw,
    )


def _ctx(*, policy=None, fsa=None) -> PricingContext:
    ctx = PricingContext()
    ctx.fsa_rates = fsa or []
    ctx.merchant_policy = policy
    return ctx


def _codes(b) -> list[str]:
    return [i.code for i in b.items]


# ------------------------------------------------------------ config parsing


def test_an_absent_config_yields_platform_defaults():
    p = policy_from_config(None)
    assert p.pricing_model == "auto"
    assert p.charge_downtown and p.charge_upper_zone
    assert p.size_tiers == []


@pytest.mark.parametrize("junk", [{"pricing_model": "nonsense"}, {"pricing_model": 42}, "notadict"])
def test_a_malformed_model_falls_back_to_auto(junk):
    """pricing_config is a free-form column, so junk must not break a quote."""
    assert policy_from_config(junk).pricing_model == "auto"


def test_malformed_tier_rows_are_dropped_not_fatal():
    p = policy_from_config({"size_tiers": ["nope", None, {"surcharge_cents": 500}]})
    assert len(p.size_tiers) == 1
    assert p.size_tiers[0].surcharge_cents == 500


def test_surcharges_default_to_charged_when_unspecified():
    p = policy_from_config({"surcharges": {"downtown": False}})
    assert p.charge_downtown is False
    assert p.charge_upper_zone is True


# -------------------------------------------------------------- unit maths


def test_imperial_limits_convert_to_metric():
    tier = SizeTier(max_length=1, dimension_unit="ft", max_weight=1, weight_unit="lb")
    assert tier.limits_cm()[0] == pytest.approx(30.48)
    assert tier.limit_kg() == pytest.approx(0.45359237)


def test_inches_convert_to_metric():
    tier = SizeTier(max_length=10, dimension_unit="in")
    assert tier.limits_cm()[0] == pytest.approx(25.4)


def test_a_blank_limit_is_unbounded():
    tier = SizeTier(max_weight=None, weight_unit="kg")
    assert tier.accepts(length_cm=999, width_cm=999, height_cm=999, weight_kg=9999)


def test_duplicate_limit_values_are_all_enforced():
    """Regression: three identical limits must not collapse into one check."""
    tier = SizeTier(max_length=10, max_width=10, max_height=10, dimension_unit="cm")
    assert tier.accepts(length_cm=5, width_cm=5, height_cm=5, weight_kg=None)
    assert not tier.accepts(length_cm=5, width_cm=5, height_cm=20, weight_kg=None)


def test_an_unknown_dimension_cannot_trigger_a_charge():
    """A booking that omits height must not be billed as oversize."""
    tier = SizeTier(max_height=10, dimension_unit="cm")
    assert tier.accepts(length_cm=5, width_cm=5, height_cm=None, weight_kg=None)


# ------------------------------------------------------------- tier billing


def _tiers():
    return [
        SizeTier(label="Small", max_length=30, max_weight=5, surcharge_cents=0),
        SizeTier(label="Medium", max_length=100, max_weight=25, surcharge_cents=1500),
        SizeTier(label="Oversize", surcharge_cents=4500),  # catch-all
    ]


def test_the_first_matching_row_wins():
    q = SizeWeightService().quote_tiers(_tiers(), weight_kg=3, dimensions={"length": 20})
    assert q.metadata["tier_index"] == 0
    assert q.total_cents == 0


def test_a_shipment_too_heavy_for_the_small_row_falls_to_medium():
    q = SizeWeightService().quote_tiers(_tiers(), weight_kg=20, dimensions={"length": 20})
    assert q.metadata["tier_label"] == "Medium"
    assert q.total_cents == 1500


def test_a_catch_all_row_absorbs_anything():
    q = SizeWeightService().quote_tiers(_tiers(), weight_kg=900, dimensions={"length": 900})
    assert q.metadata["tier_label"] == "Oversize"
    assert q.total_cents == 4500


def test_without_a_catch_all_an_unmatched_shipment_is_not_charged():
    """Never invent a fee for a shipment the merchant never priced."""
    tiers = [SizeTier(label="Small", max_weight=5, surcharge_cents=1000)]
    q = SizeWeightService().quote_tiers(tiers, weight_kg=500)
    assert q.total_cents == 0
    assert q.metadata["matched"] is False


def test_pounds_are_compared_against_kilogram_shipments():
    tiers = [SizeTier(label="Under 10 lb", max_weight=10, weight_unit="lb", surcharge_cents=500)]
    svc = SizeWeightService()
    assert svc.quote_tiers(tiers, weight_kg=4).total_cents == 500  # 4 kg ≈ 8.8 lb
    assert svc.quote_tiers(tiers, weight_kg=6).total_cents == 0  # 6 kg ≈ 13.2 lb


# -------------------------------------------------------- engine integration


def test_a_merchant_table_replaces_the_rate_card_thresholds():
    policy = MerchantPricingPolicy(size_tiers=_tiers())
    result = PricingEngine().calculate(_request(weight_kg=20), _ctx(policy=policy))
    assert "size_tier" in _codes(result)
    assert "overweight" not in _codes(result)


def test_waiving_downtown_removes_the_fee_but_records_the_trip():
    policy = MerchantPricingPolicy(charge_downtown=False)
    result = PricingEngine().calculate(_request(), _ctx(policy=policy))
    assert "downtown" not in _codes(result)
    # The drop really is downtown — ops should see it was waived, not missed.
    assert result.metadata["is_downtown"] is True
    assert result.metadata["downtown_waived"] is True


def test_charging_downtown_is_the_default():
    result = PricingEngine().calculate(_request(), _ctx())
    assert "downtown" in _codes(result)
    assert "downtown_waived" not in result.metadata


def test_a_distance_merchant_ignores_an_available_fsa_rate():
    rates = [FsaRateRecord(id="r1", dest_fsa="M5V", flat_cents=1800)]
    policy = MerchantPricingPolicy(pricing_model="distance")
    result = PricingEngine().calculate(_request(), _ctx(policy=policy, fsa=rates))
    assert result.metadata["pricing_model"] == "gta_delivery_rate"
    assert "fsa_rate" not in _codes(result)


def test_an_fsa_merchant_uses_the_rate():
    rates = [FsaRateRecord(id="r1", dest_fsa="M5V", flat_cents=1800)]
    policy = MerchantPricingPolicy(pricing_model="fsa")
    result = PricingEngine().calculate(_request(), _ctx(policy=policy, fsa=rates))
    assert result.metadata["pricing_model"] == "fsa_flat_rate"


def test_an_fsa_merchant_still_gets_a_quote_where_no_rate_exists():
    """Coverage gaps must never block a booking — they get flagged instead."""
    rates = [FsaRateRecord(id="r1", dest_fsa="K1A", flat_cents=1800)]
    policy = MerchantPricingPolicy(pricing_model="fsa")
    result = PricingEngine().calculate(_request(), _ctx(policy=policy, fsa=rates))
    assert result.metadata["pricing_model"] == "gta_delivery_rate"
    assert result.metadata["fsa_fallback"] is True
    assert result.final_cents > 0


def test_fsa_miss_refuse_skips_distance_fallback():
    from porterchain_pricing.policy import MerchantSchedule

    rates = [FsaRateRecord(id="r1", dest_fsa="K1A", flat_cents=1800)]
    policy = MerchantPricingPolicy(
        pricing_model="fsa",
        schedule=MerchantSchedule(fsa_miss="refuse"),
    )
    result = PricingEngine().calculate(_request(), _ctx(policy=policy, fsa=rates))
    assert result.metadata.get("fsa_refused") is True
    assert "fsa_fallback" not in result.metadata
    assert result.base_cents == 0


def test_schedule_fuel_override_zero_skips_platform_fuel():
    from porterchain_pricing.policy import MerchantSchedule
    from porterchain_pricing.types import FuelConfig

    rates = [FsaRateRecord(id="r1", dest_fsa="M5V", flat_cents=3000)]
    policy = MerchantPricingPolicy(
        pricing_model="fsa",
        schedule=MerchantSchedule(fuel_surcharge_percent=0),
    )
    ctx = _ctx(policy=policy, fsa=rates)
    ctx.fuel = FuelConfig(surcharge_percent=5.0)
    result = PricingEngine().calculate(_request(), ctx)
    assert "fuel" not in _codes(result)
    assert result.metadata.get("fuel_surcharge_percent") == 0


def test_origin_pickup_and_route_minimum_top_up():
    from porterchain_pricing.policy import MerchantSchedule

    rates = [
        FsaRateRecord(
            id="r1", dest_fsa="M5V", flat_cents=3000, config={"tier": "T1"}
        )
    ]
    policy = MerchantPricingPolicy(
        pricing_model="fsa",
        schedule=MerchantSchedule(
            fuel_surcharge_percent=0,
            origin_pickup_cents=4000,
            origin_pickup_vehicle_classes=["cargo_van"],
            route_minimums_cents={"T1": 12000},
        ),
    )
    result = PricingEngine().calculate(_request(), _ctx(policy=policy, fsa=rates))
    assert "origin_pickup" in _codes(result)
    assert "route_minimum" in _codes(result)
    # 30 + 40 = 70 → floor 120 → top-up 50
    assert result.metadata["route_minimum_cents"] == 12000
    pre_tax = sum(i.amount_cents for i in result.items)
    assert pre_tax == 12000


def test_schedule_parses_from_config():
    p = policy_from_config(
        {
            "schedule": {
                "fuel_surcharge_percent": 0,
                "fsa_miss": "refuse",
                "origin_pickup_cents": 4000,
                "size_match": "any",
            }
        }
    )
    assert p.schedule.fuel_surcharge_percent == 0
    assert p.schedule.fsa_miss == "refuse"
    assert p.schedule.origin_pickup_cents == 4000
    assert p.schedule.size_match == "any"


def test_kaylulu_pdf_sample_t1_pickup_floors_to_120():
    """PDF: T1 $30 + $40 pickup = $70 → route min $120."""
    from porterchain_pricing.policy import MerchantSchedule
    from porterchain_pricing.types import FuelConfig

    rates = [
        FsaRateRecord(id="r1", dest_fsa="L5M", flat_cents=3000, config={"tier": "T1"})
    ]
    policy = MerchantPricingPolicy(
        pricing_model="fsa",
        schedule=MerchantSchedule(
            fuel_surcharge_percent=0,
            fsa_miss="refuse",
            origin_pickup_cents=4000,
            route_minimums_cents={"T1": 12000, "T2": 20000, "T3": 25000},
        ),
    )
    drop = GeoPoint(lat=43.58, lng=-79.72, formatted="Mississauga", postal="L5M 1A1")
    ctx = _ctx(policy=policy, fsa=rates)
    ctx.fuel = FuelConfig(surcharge_percent=5.0)
    result = PricingEngine().calculate(
        _request(dropoff=drop, weight_kg=20),
        ctx,
    )
    assert "fuel" not in _codes(result)
    assert sum(i.amount_cents for i in result.items) == 12000


def test_kaylulu_pdf_sample_handling_plus_min():
    """PDF: T1 + $30 handling + pickup under min still floors to $120."""
    from porterchain_pricing.policy import MerchantSchedule, SizeTier

    rates = [
        FsaRateRecord(id="r1", dest_fsa="L5M", flat_cents=3000, config={"tier": "T1"})
    ]
    policy = MerchantPricingPolicy(
        pricing_model="fsa",
        size_tiers=[
            SizeTier(label="Standard", max_weight=50, weight_unit="lb", surcharge_cents=0),
            SizeTier(label="Large", max_weight=110, weight_unit="lb", surcharge_cents=3000),
            SizeTier(label="XL", surcharge_cents=6000),
        ],
        schedule=MerchantSchedule(
            fuel_surcharge_percent=0,
            origin_pickup_cents=4000,
            route_minimums_cents={"T1": 12000},
        ),
    )
    drop = GeoPoint(lat=43.58, lng=-79.72, formatted="Mississauga", postal="L5M 1A1")
    # ~99 lb ≈ 45 kg → Large +$30; true bill 30+40+30=100 → floor 120
    result = PricingEngine().calculate(
        _request(dropoff=drop, weight_kg=45.0),
        _ctx(policy=policy, fsa=rates),
    )
    assert "size_tier" in _codes(result)
    assert sum(i.amount_cents for i in result.items) == 12000


def test_no_fallback_flag_when_the_merchant_never_asked_for_fsa():
    result = PricingEngine().calculate(_request(), _ctx())
    assert "fsa_fallback" not in result.metadata
