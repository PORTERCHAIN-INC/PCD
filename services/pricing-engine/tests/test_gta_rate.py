"""GTA delivery rate matrix — product quote formula."""

from __future__ import annotations

from porterchain_pricing.components import DistanceRateService, LocationSurchargeService, StopFeeService
from porterchain_pricing.gta_rate import GtaRateConfig, normalize_vehicle_type
from porterchain_pricing.pricing_service import PricingService
from porterchain_pricing.types import GeoPoint, PricingContext, PricingRequest, TaxConfig


def _matrix_cents(
    *,
    vehicle_type: str,
    total_km: float,
    total_pickups: int = 1,
    total_drops: int = 1,
    is_downtown: bool = False,
    is_upper_zone: bool = False,
    config: GtaRateConfig | None = None,
) -> int:
    """Distance + stop fees + location surcharges — the components the engine sums."""
    return (
        DistanceRateService().quote(vehicle_type=vehicle_type, total_km=total_km, config=config).total_cents
        + StopFeeService()
        .quote(
            vehicle_type=vehicle_type,
            total_pickups=total_pickups,
            total_drops=total_drops,
            config=config,
        )
        .total_cents
        + LocationSurchargeService()
        .quote(is_downtown=is_downtown, is_upper_zone=is_upper_zone, config=config)
        .total_cents
    )


def test_sprinter_15_drops_18km_is_285():
    """1 pickup, 15 drops, 18 km, large van → $285.00."""
    cents = _matrix_cents(vehicle_type="sprinter_van", total_km=18, total_pickups=1, total_drops=15)
    assert cents == 28500


def test_vehicle_aliases_map_to_matrix():
    assert normalize_vehicle_type("highRoof") == "sprinter_van"
    assert normalize_vehicle_type("cargoVan") == "cargo_van"
    assert normalize_vehicle_type("box16") == "box_16"
    assert normalize_vehicle_type("sedan") == "sedan_suv"
    assert normalize_vehicle_type("sprinter_van") == "sprinter_van"


def test_extra_km_beyond_20():
    # sedan_suv base 45 + 5 * 1.25 = 51.25
    assert _matrix_cents(vehicle_type="sedan", total_km=25) == 5125
    assert normalize_vehicle_type("sedan") == "sedan_suv"


def test_location_surcharges_once_each():
    cents = _matrix_cents(vehicle_type="suv", total_km=10, is_downtown=True, is_upper_zone=True)
    # sedan_suv 45 + 25 + 15 = 85 (suv collapses into sedan_suv)
    assert cents == 8500
    assert normalize_vehicle_type("suv") == "sedan_suv"


def test_retail_engine_matches_matrix_via_additional_stops():
    svc = PricingService()
    # 1 dropoff + 14 additional = 15 drops
    stops = [GeoPoint(lat=43.70, lng=-79.40) for _ in range(14)]
    req = PricingRequest(
        pickup=GeoPoint(lat=43.65, lng=-79.38, formatted="Toronto"),
        dropoff=GeoPoint(lat=43.71, lng=-79.39, formatted="Toronto"),
        vehicle_class="highRoof",
        distance_meters=18_000,
        additional_stops=stops,
        is_downtown=False,
        is_upper_zone=False,
    )
    breakdown = svc.calculate_retail(req)
    assert breakdown.final_cents == 28500
    assert breakdown.metadata.get("pricing_model") == "gta_delivery_rate"
    assert breakdown.metadata.get("gta_vehicle_type") == "sprinter_van"


def test_admin_config_override_changes_quote():
    from porterchain_pricing.gta_rate import gta_rate_config_from_dict

    cfg = gta_rate_config_from_dict(
        {
            "vehicles": {
                "sprinter_van": {
                    "base_price": 80.0,
                    "extra_km_rate": 2.5,
                    "extra_pick_fee": 20.0,
                    "extra_drop_fee": 15.0,
                }
            }
        }
    )
    cents = _matrix_cents(
        vehicle_type="sprinter_van", total_km=18, total_pickups=1, total_drops=15, config=cfg
    )
    assert cents == 29000


def test_tax_zero_by_default_matches_clean_quote():
    from porterchain_pricing.engine import PricingEngine

    req = PricingRequest(
        pickup=GeoPoint(lat=43.65, lng=-79.38),
        dropoff=GeoPoint(lat=43.66, lng=-79.39),
        vehicle_class="sedan",
        distance_meters=10_000,
        total_pickups=1,
        total_drops=1,
        is_downtown=False,
        is_upper_zone=False,
    )
    breakdown = PricingEngine().calculate(req, PricingContext(tax=TaxConfig(hst_percent=0.0)))
    assert breakdown.final_cents == 4500
    assert breakdown.tax_cents == 0


def test_merge_merchant_gta_overlay_uses_platform_as_base():
    from porterchain_pricing.engine import PricingEngine
    from porterchain_pricing.gta_rate import default_gta_rate_config, merge_merchant_gta_overlay
    from porterchain_pricing.policy import MerchantPricingPolicy

    system = default_gta_rate_config()
    system.vehicles["cargo_van"] = {
        **system.vehicles["cargo_van"],
        "base_price": 65.0,
    }
    merchant_a = merge_merchant_gta_overlay(
        system, {"gta_rate": {"vehicles": {"cargo_van": {"base_price": 50.0}}}}
    )
    merchant_b = merge_merchant_gta_overlay(
        system, {"gta_rate": {"vehicles": {"cargo_van": {"base_price": 90.0}}}}
    )
    assert merchant_a.vehicles["cargo_van"]["base_price"] == 50.0
    assert merchant_b.vehicles["cargo_van"]["base_price"] == 90.0
    # Untouched keys stay on the platform card
    assert merchant_a.vehicles["cargo_van"]["extra_km_rate"] == system.vehicles["cargo_van"]["extra_km_rate"]

    req = PricingRequest(
        pickup=GeoPoint(lat=43.65, lng=-79.38),
        dropoff=GeoPoint(lat=43.66, lng=-79.39),
        vehicle_class="cargo_van",
        channel="merchant",
        merchant_id="m-a",
        distance_meters=10_000,
        total_pickups=1,
        total_drops=1,
        is_downtown=False,
        is_upper_zone=False,
    )
    policy = MerchantPricingPolicy(pricing_model="distance")
    a = PricingEngine().calculate(
        req, PricingContext(gta_rate=merchant_a, merchant_policy=policy)
    )
    b = PricingEngine().calculate(
        req, PricingContext(gta_rate=merchant_b, merchant_policy=policy)
    )
    assert a.base_cents == 5000
    assert b.base_cents == 9000
    assert a.base_cents != b.base_cents


def test_customer_sedan_suv_28km_extra_drop_downtown_is_95():
    from porterchain_pricing.gta_rate import customer_gta_from_dict, default_customer_distance_dict

    cfg = customer_gta_from_dict(default_customer_distance_dict())
    cents = _matrix_cents(
        vehicle_type="sedan_suv", total_km=28, total_pickups=1, total_drops=2, is_downtown=True, config=cfg
    )
    assert cents == 9500


def test_stored_suv_matches_sedan_suv():
    from porterchain_pricing.components.fsa import FsaRateService
    from porterchain_pricing.gta_rate import vehicle_classes_match
    from porterchain_pricing.types import FsaRateRecord

    assert vehicle_classes_match("suv", "sedan_suv")
    assert vehicle_classes_match("box_truck", "box_16")
    chosen = FsaRateService().select(
        [FsaRateRecord(id="1", dest_fsa="M5V", flat_cents=1800, vehicle_class="suv")],
        dest_fsa="M5V",
        vehicle_class="sedan_suv",
    )
    assert chosen is not None
    assert chosen.flat_cents == 1800


def test_legacy_gta_keys_collapse_to_catalog():
    from porterchain_pricing.gta_rate import gta_rate_config_from_dict

    cfg = gta_rate_config_from_dict(
        {
            "vehicles": {
                "sedan": {"base_price": 45.0, "extra_km_rate": 1.25, "extra_pick_fee": 20.0, "extra_drop_fee": 15.0},
                "suv": {"base_price": 55.0, "extra_km_rate": 1.75, "extra_pick_fee": 20.0, "extra_drop_fee": 15.0},
                "box_truck": {
                    "base_price": 125.0,
                    "extra_km_rate": 3.5,
                    "extra_pick_fee": 20.0,
                    "extra_drop_fee": 15.0,
                },
            }
        }
    )
    assert "sedan" not in cfg.vehicles
    assert "suv" not in cfg.vehicles
    assert "box_truck" not in cfg.vehicles
    assert cfg.vehicles["sedan_suv"]["base_price"] == 45.0
    assert cfg.vehicles["box_16"]["base_price"] == 125.0
    assert "box_20" in cfg.vehicles
