"""GTA delivery rate matrix — product quote formula."""

from __future__ import annotations

from porterchain_pricing.gta_rate import calculate_gta_delivery_rate, normalize_vehicle_type
from porterchain_pricing.pricing_service import PricingService
from porterchain_pricing.types import GeoPoint, PricingContext, PricingRequest, TaxConfig


def test_sprinter_15_drops_18km_is_285():
    """1 pickup, 15 drops, 18 km, large van → $285.00."""
    result = calculate_gta_delivery_rate(
        vehicle_type="sprinter_van",
        total_km=18,
        total_pickups=1,
        total_drops=15,
        is_downtown=False,
        is_upper_zone=False,
    )
    assert result.total_cad == 285.0
    assert result.total_cents == 28500


def test_vehicle_aliases_map_to_matrix():
    assert normalize_vehicle_type("highRoof") == "sprinter_van"
    assert normalize_vehicle_type("cargoVan") == "cargo_van"
    assert normalize_vehicle_type("box16") == "box_truck"
    assert normalize_vehicle_type("sprinter_van") == "sprinter_van"


def test_extra_km_beyond_20():
    # sedan base 45 + 5 * 1.25 = 51.25
    result = calculate_gta_delivery_rate(vehicle_type="sedan", total_km=25, total_pickups=1, total_drops=1)
    assert result.total_cad == 51.25


def test_location_surcharges_once_each():
    result = calculate_gta_delivery_rate(
        vehicle_type="suv",
        total_km=10,
        total_pickups=1,
        total_drops=1,
        is_downtown=True,
        is_upper_zone=True,
    )
    # 55 + 25 + 15 = 95
    assert result.total_cad == 95.0


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
    result = calculate_gta_delivery_rate(
        vehicle_type="sprinter_van",
        total_km=18,
        total_pickups=1,
        total_drops=15,
        config=cfg,
    )
    assert result.total_cad == 290.0


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
