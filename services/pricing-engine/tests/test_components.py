"""Each pricing component, priced on its own."""

import pytest

from porterchain_pricing.components import (
    DistanceRateService,
    FsaRateService,
    LocationSurchargeService,
    SizeWeightService,
    StopFeeService,
    fsa_from_point,
    is_ontario_fsa,
    normalize_fsa,
)
from porterchain_pricing.components.size_weight import parse_volume_cm3
from porterchain_pricing.gta_rate import calculate_gta_delivery_rate, default_gta_rate_config
from porterchain_pricing.types import FsaRateRecord, GeoPoint, SizeWeightConfig


# ------------------------------------------------------------------ distance


def test_distance_under_base_km_charges_base_only():
    q = DistanceRateService().quote(vehicle_type="cargo_van", total_km=12)
    assert q.metadata["extra_km"] == 0
    assert [i.code for i in q.items] == ["base"]


def test_distance_beyond_base_km_adds_a_separate_extra_km_line():
    cfg = default_gta_rate_config()
    q = DistanceRateService().quote(vehicle_type="cargo_van", total_km=cfg.base_km_limit + 10)
    codes = [i.code for i in q.items]
    assert codes == ["base", "extra_km"]
    rate = cfg.vehicle("cargo_van")["extra_km_rate"]
    assert q.items[1].amount_cents == int(round(10 * float(rate) * 100))


def test_distance_treats_negative_km_as_zero():
    q = DistanceRateService().quote(vehicle_type="cargo_van", total_km=-50)
    assert q.metadata["total_km"] == 0.0
    assert q.metadata["extra_km"] == 0


# --------------------------------------------------------------------- stops


def test_first_pickup_and_drop_are_free():
    q = StopFeeService().quote(vehicle_type="cargo_van", total_pickups=1, total_drops=1)
    assert q.total_cents == 0
    assert not q.applies


def test_extra_stops_are_charged_per_stop():
    svc = StopFeeService()
    one = svc.quote(vehicle_type="cargo_van", total_pickups=1, total_drops=2)
    two = svc.quote(vehicle_type="cargo_van", total_pickups=1, total_drops=3)
    assert two.total_cents == one.total_cents * 2


# ------------------------------------------------------------------ location


def test_location_flags_can_be_forced_without_coordinates():
    cfg = default_gta_rate_config()
    q = LocationSurchargeService().quote(is_downtown=True, is_upper_zone=False)
    assert q.total_cents == int(round(float(cfg.downtown_fee_cad) * 100))
    assert [i.code for i in q.items] == ["downtown"]


def test_each_location_fee_applies_at_most_once():
    q = LocationSurchargeService().quote(is_downtown=True, is_upper_zone=True)
    assert [i.code for i in q.items] == ["downtown", "upper_zone"]


# -------------------------------------------------------- distance ≡ matrix


def test_components_sum_to_the_gta_matrix_total():
    """The matrix is built from the components, so the two must never diverge."""
    cfg = default_gta_rate_config()
    args = dict(vehicle_type="box_truck", total_km=45.0, total_pickups=2, total_drops=3)
    matrix = calculate_gta_delivery_rate(**args, is_downtown=True, is_upper_zone=True, config=cfg)

    parts = (
        DistanceRateService().quote(
            vehicle_type=args["vehicle_type"], total_km=args["total_km"], config=cfg
        ).total_cents
        + StopFeeService().quote(
            vehicle_type=args["vehicle_type"],
            total_pickups=args["total_pickups"],
            total_drops=args["total_drops"],
            config=cfg,
        ).total_cents
        + LocationSurchargeService()
        .quote(is_downtown=True, is_upper_zone=True, config=cfg)
        .total_cents
    )
    assert parts == int(round(matrix.total_cad * 100))


# --------------------------------------------------------------- size/weight


def test_size_weight_charges_nothing_when_the_rate_card_is_unset():
    q = SizeWeightService().quote(weight_kg=500, declared_value_cents=100_000)
    assert q.total_cents == 0
    assert not q.applies


def test_only_weight_above_the_threshold_is_billable():
    cfg = SizeWeightConfig(weight_threshold_kg=100, weight_cents_per_kg=50)
    svc = SizeWeightService()
    assert svc.quote(weight_kg=80, config=cfg).total_cents == 0
    assert svc.quote(weight_kg=150, config=cfg).total_cents == 50 * 50


def test_declared_value_is_charged_on_the_insurable_excess():
    cfg = SizeWeightConfig(declared_value_threshold_cents=10_000, declared_value_rate=0.02)
    q = SizeWeightService().quote(declared_value_cents=110_000, config=cfg)
    assert q.total_cents == int(round(100_000 * 0.02))


@pytest.mark.parametrize(
    "value,expected",
    [
        ({"length": 10, "width": 20, "height": 30}, 6000.0),
        ("10x20x30", 6000.0),
        ("10 x 20 x 30 cm", 6000.0),
        ("not a size", 0.0),
        ("10x20", 0.0),
        (None, 0.0),
    ],
)
def test_volume_parsing_never_invents_a_charge(value, expected):
    assert parse_volume_cm3(value) == expected


# ----------------------------------------------------------------------- FSA


@pytest.mark.parametrize(
    "value,expected",
    [
        ("M5V 2T6", "M5V"), ("m5v2t6", "M5V"), ("M5V", "M5V"),
        ("", ""), (None, ""), ("12345", ""), ("MMM", ""),
    ],
)
def test_fsa_normalization(value, expected):
    assert normalize_fsa(value) == expected


def test_fsa_is_read_from_the_postal_field_first():
    point = GeoPoint(formatted="123 King St W, Toronto, ON L4W 5N5", postal="M5V 2T6")
    assert fsa_from_point(point) == "M5V"


def test_fsa_falls_back_to_the_formatted_address():
    assert fsa_from_point(GeoPoint(formatted="123 King St W, Toronto, ON M5V 2T6")) == "M5V"
    assert fsa_from_point(GeoPoint(formatted="somewhere with no postal code")) == ""


def test_ontario_prefixes():
    assert is_ontario_fsa("M5V")
    assert is_ontario_fsa("L4W")
    assert not is_ontario_fsa("V6B")  # British Columbia
    assert not is_ontario_fsa("")


def _rate(rid, dest, cents, **kw):
    return FsaRateRecord(id=rid, dest_fsa=dest, flat_cents=cents, **kw)


def test_no_rate_matches_a_different_destination():
    q = FsaRateService().quote([_rate("a", "M5V", 1800)], dest_fsa="L4W")
    assert not q.applies
    assert q.metadata["reason"] == "no_matching_rate"


def test_missing_destination_is_reported_not_guessed():
    q = FsaRateService().quote([_rate("a", "M5V", 1800)], dropoff=GeoPoint(formatted="nowhere"))
    assert not q.applies
    assert q.metadata["reason"] == "no_destination_fsa"


def test_merchant_rate_beats_the_platform_rate():
    rates = [_rate("global", "M5V", 2500), _rate("mine", "M5V", 1800, merchant_id="m1")]
    picked = FsaRateService().select(rates, dest_fsa="M5V", merchant_id="m1")
    assert picked.id == "mine"


def test_one_merchants_rate_never_applies_to_another():
    rates = [_rate("global", "M5V", 2500), _rate("theirs", "M5V", 900, merchant_id="m2")]
    picked = FsaRateService().select(rates, dest_fsa="M5V", merchant_id="m1")
    assert picked.id == "global"


def test_a_lane_beats_a_destination_only_rate():
    rates = [_rate("any_origin", "M5V", 2500), _rate("lane", "M5V", 1800, origin_fsa="L4W")]
    picked = FsaRateService().select(rates, dest_fsa="M5V", origin_fsa="L4W")
    assert picked.id == "lane"
    # A different origin falls back to the any-origin row.
    assert FsaRateService().select(rates, dest_fsa="M5V", origin_fsa="M4B").id == "any_origin"


def test_vehicle_specific_rate_beats_the_any_vehicle_rate():
    rates = [_rate("any", "M5V", 2500), _rate("truck", "M5V", 4000, vehicle_class="box_truck")]
    assert FsaRateService().select(rates, dest_fsa="M5V", vehicle_class="box_truck").id == "truck"
    assert FsaRateService().select(rates, dest_fsa="M5V", vehicle_class="sedan").id == "any"


def test_equally_specific_rates_resolve_to_the_cheaper_one():
    rates = [_rate("a", "M5V", 2500), _rate("b", "M5V", 1800)]
    assert FsaRateService().select(rates, dest_fsa="M5V").id == "b"


def test_inactive_rates_are_ignored():
    rates = [_rate("off", "M5V", 900, is_active=False), _rate("on", "M5V", 2500)]
    assert FsaRateService().select(rates, dest_fsa="M5V").id == "on"
