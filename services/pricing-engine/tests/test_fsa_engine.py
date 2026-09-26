"""FSA rates inside a full quote: precedence, replacement and surcharge handling."""

from porterchain_pricing.engine import PricingEngine
from porterchain_pricing.types import (
    FsaRateRecord,
    GeoPoint,
    PricingContext,
    PricingRequest,
    TariffRecord,
)

# Mississauga warehouse to a downtown Toronto address, far enough apart that the
# distance matrix and a flat rate give obviously different numbers.
PICKUP = GeoPoint(lat=43.5890, lng=-79.6441, formatted="Mississauga, ON", postal="L4W 5N5")
DROPOFF = GeoPoint(lat=43.6426, lng=-79.3871, formatted="Toronto, ON", postal="M5V 2T6")


def _request(**kw) -> PricingRequest:
    return PricingRequest(
        pickup=PICKUP,
        dropoff=DROPOFF,
        vehicle_class=kw.pop("vehicle_class", "cargo_van"),
        channel=kw.pop("channel", "merchant"),
        merchant_id=kw.pop("merchant_id", "m1"),
        **kw,
    )


def _ctx(rates: list[FsaRateRecord] | None = None, **kw) -> PricingContext:
    ctx = PricingContext(**kw)
    ctx.fsa_rates = rates or []
    return ctx


def _codes(breakdown) -> list[str]:
    return [i.code for i in breakdown.items]


def test_without_a_matching_rate_the_gta_matrix_still_prices_the_trip():
    result = PricingEngine().calculate(_request(), _ctx())
    assert result.metadata["pricing_model"] == "gta_delivery_rate"
    assert "fsa_rate" not in _codes(result)


def test_a_matching_rate_replaces_the_distance_charge():
    rates = [FsaRateRecord(id="r1", dest_fsa="M5V", flat_cents=1800, merchant_id="m1")]
    result = PricingEngine().calculate(_request(), _ctx(rates))

    assert result.metadata["pricing_model"] == "fsa_flat_rate"
    assert result.base_cents == 1800
    # The whole point: no base or extra-km line survives alongside the flat rate.
    assert "base" not in _codes(result)
    assert "extra_km" not in _codes(result)
    assert result.distance_cents == 0


def test_an_all_in_rate_suppresses_the_downtown_surcharge():
    """M5V is downtown, so an all-in flat rate must not then add the downtown fee."""
    rates = [FsaRateRecord(id="r1", dest_fsa="M5V", flat_cents=1800, includes_location_fees=True)]
    result = PricingEngine().calculate(_request(), _ctx(rates))
    assert "downtown" not in _codes(result)


def test_a_non_all_in_rate_still_adds_location_surcharges():
    rates = [FsaRateRecord(id="r1", dest_fsa="M5V", flat_cents=1800, includes_location_fees=False)]
    result = PricingEngine().calculate(_request(), _ctx(rates))
    assert "downtown" in _codes(result)


def test_extra_stops_are_billed_even_on_a_flat_rate():
    """A flat rate covers geography, not the extra work of more stops."""
    rates = [FsaRateRecord(id="r1", dest_fsa="M5V", flat_cents=1800)]
    engine, ctx = PricingEngine(), _ctx(rates)
    one_stop = engine.calculate(_request(), ctx)
    three_stops = engine.calculate(_request(total_drops=3), _ctx(rates))

    assert "stop_fees" in _codes(three_stops)
    assert three_stops.final_cents > one_stop.final_cents


def test_a_merchant_tariff_takes_precedence_over_an_fsa_rate():
    """Contract terms are negotiated; FSA rates are a rate-card default."""
    rates = [FsaRateRecord(id="r1", dest_fsa="M5V", flat_cents=1800)]
    ctx = _ctx(rates)
    ctx.tariffs = [
        TariffRecord(id="t1", name="Negotiated", tariff_type="flat", merchant_id="m1", base_cents=9900)
    ]
    result = PricingEngine().calculate(_request(), ctx)
    assert result.base_cents == 9900
    # The FSA table is never even consulted once a tariff has set the base.
    assert result.metadata.get("pricing_model") != "fsa_flat_rate"
    assert "fsa" not in result.metadata


def test_the_fsa_lookup_is_recorded_even_when_nothing_matches():
    """Ops needs to see why a quote fell through to the distance matrix."""
    rates = [FsaRateRecord(id="r1", dest_fsa="K1A", flat_cents=1800)]
    result = PricingEngine().calculate(_request(), _ctx(rates))
    fsa = result.metadata["fsa"]
    assert fsa["matched"] is False
    assert fsa["dest_fsa"] == "M5V"
    assert fsa["origin_fsa"] == "L4W"


def test_a_retail_quote_ignores_platform_wide_fsa_rates():
    rates = [FsaRateRecord(id="r1", dest_fsa="M5V", flat_cents=2500)]
    result = PricingEngine().calculate(
        _request(channel="retail", merchant_id=None), _ctx(rates)
    )
    assert result.metadata["pricing_model"] == "gta_delivery_rate"
    assert "fsa_rate" not in _codes(result)


def test_global_retail_and_merchant_catalog_tariffs_do_not_steal_fsa():
    """Production/local seeds used to match every merchant quote and skip FSA."""
    rates = [FsaRateRecord(id="r1", dest_fsa="M5V", flat_cents=1800, merchant_id="m1")]
    ctx = _ctx(rates)
    ctx.tariffs = [
        TariffRecord(
            id="retail",
            name="GTA Standard Cargo Van",
            tariff_type="retail",
            vehicle_class="cargo_van",
            zone="gta",
            base_cents=1200,
            per_km_cents=95,
        ),
        TariffRecord(
            id="merchant-global",
            name="GTA Merchant Cargo Van",
            tariff_type="merchant",
            vehicle_class="cargo_van",
            zone="gta",
            base_cents=1500,
            per_km_cents=110,
        ),
    ]
    ctx.merchant_pricing_config = {"surcharges": {"downtown": True, "upper_zone": True}}
    result = PricingEngine().calculate(_request(), ctx)
    assert result.metadata["pricing_model"] == "fsa_flat_rate"
    assert result.base_cents == 1800


def test_merchant_scoped_tariff_still_beats_fsa():
    rates = [FsaRateRecord(id="r1", dest_fsa="M5V", flat_cents=1800, merchant_id="m1")]
    ctx = _ctx(rates)
    ctx.tariffs = [
        TariffRecord(
            id="scoped",
            name="Negotiated merchant",
            tariff_type="merchant",
            merchant_id="m1",
            vehicle_class="cargo_van",
            base_cents=7700,
            per_km_cents=0,
        )
    ]
    result = PricingEngine().calculate(_request(), ctx)
    assert result.base_cents == 7700
    assert result.metadata.get("pricing_model") == "contract_tariff"
