"""Kaylulu contract schedule wiring: coverage, Shopify parcels/vehicle, admin editor, template."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from porterchain_pricing.engine import PricingEngine
from porterchain_pricing.policy import policy_from_config
from porterchain_pricing.types import PricingContext

from porterchain_api.admin_engine.fsa_admin_service import FsaAdminService
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.integrations.shopify_carrier_rates import (
    carrier_service_rates,
    parcels_from_items,
    quote_merchant_rate,
    resolve_shopify_vehicle,
)
from porterchain_api.merchant_engine.booking_validation import (
    BookingValidationError,
    assert_not_fsa_refused,
)
from porterchain_api.merchant_engine.kaylulu_template import kaylulu_pricing_config
from porterchain_api.merchant_engine.service_area import (
    assert_ontario_booking,
    merchant_coverage_fsas,
    service_area_error,
)
from porterchain_api.merchant_engine.shopify_fulfillment_ops import _reject_reason
from porterchain_api.merchant_engine.stop_cargo import parcels_for_pricing
from porterchain_api.schemas_merchant import (
    AddressInput,
    MerchantBookDeliveryRequest,
    RouteImportPackageInput,
)
from porterchain_api.schemas_pricing import FsaRateBody

REGISTRY_GAPS = ("L5P", "M7R", "M7A", "M7Y", "L3E", "L3J", "L3W", "N6H", "N6J", "N6K")


def _kaylulu(**overrides):
    base = dict(
        id="kay",
        status=MerchantStatus.ACTIVE.value,
        pricing_model="fsa",
        pricing_config=kaylulu_pricing_config(),
        encrypted_webhook_secret=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _addr(fsa: str) -> AddressInput:
    return AddressInput(formatted=f"1 Main St, {fsa} 1A1, ON", postal=f"{fsa}1A1", lat=43.6, lng=-79.6)


def _item(qty: int, inches: tuple[float, float, float] | None, grams: int = 2000) -> dict:
    props = []
    if inches:
        props = [
            {"name": "length", "value": str(inches[0])},
            {"name": "width", "value": str(inches[1])},
            {"name": "height", "value": str(inches[2])},
        ]
    return {"name": "Box", "quantity": qty, "grams": grams, "properties": props}


# ── coverage ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("fsa", REGISTRY_GAPS)
def test_registry_gap_fsa_is_covered_for_the_contract_merchant(fsa):
    assert service_area_error("destination", _addr(fsa)) is not None
    coverage = merchant_coverage_fsas(MagicMock(), _kaylulu())
    assert service_area_error("destination", _addr(fsa), coverage) is None


def test_contract_coverage_excludes_custom_quote_and_rural_fsas():
    coverage = merchant_coverage_fsas(MagicMock(), _kaylulu())
    assert len(coverage) == 321
    assert not {"K9J", "N7G", "L0A"} & coverage


def test_distance_merchant_gets_no_extra_coverage():
    assert merchant_coverage_fsas(MagicMock(), _kaylulu(pricing_model="distance")) == frozenset()
    assert merchant_coverage_fsas(MagicMock(), None) == frozenset()


def test_generic_fsa_merchant_coverage_is_its_own_active_rows():
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [("n6h",), ("bad",), ("M5V",)]
    merchant = SimpleNamespace(id="m2", pricing_model="fsa", pricing_config={})
    assert merchant_coverage_fsas(db, merchant) == frozenset({"N6H", "M5V"})


def test_booking_dropoff_and_stops_use_coverage_but_pickup_stays_on_tile():
    coverage = merchant_coverage_fsas(MagicMock(), _kaylulu())
    body = MerchantBookDeliveryRequest(
        pickup=_addr("L9T"),
        dropoff=_addr("N6H"),
        additional_stops=[_addr("L3W")],
        scheduled_at=datetime.now(UTC),
    )
    assert_ontario_booking(body, extra_fsas=coverage)
    with pytest.raises(BookingValidationError):
        assert_ontario_booking(body)
    flipped = body.model_copy(update={"pickup": _addr("N6H"), "dropoff": _addr("L9T")})
    with pytest.raises(BookingValidationError, match="pickup"):
        assert_ontario_booking(flipped, extra_fsas=coverage)


def test_fulfillment_request_accepts_covered_destination():
    payload = {"shipping_address": {"zip": "N6H 1A1", "country": "Canada"}}
    coverage = merchant_coverage_fsas(MagicMock(), _kaylulu())
    assert _reject_reason(payload, "SHIPPING") == "Outside the priced delivery tile."
    assert _reject_reason(payload, "SHIPPING", coverage) is None


def test_custom_quote_refusal_message():
    breakdown = SimpleNamespace(
        metadata={"fsa_refused": True, "custom_quote": True, "custom_quote_reason": "custom_quote_fsa"}
    )
    with pytest.raises(BookingValidationError, match="custom quotation"):
        assert_not_fsa_refused(breakdown)


# ── Shopify checkout ────────────────────────────────────────────────────


def _carrier(merchant, destination_postal: str, quote_return=(28250, None)):
    payload = {
        "rate": {
            "currency": "CAD",
            "origin": {"postal_code": "L9T2X5", "country": "CA", "province": "ON"},
            "destination": {
                "postal_code": destination_postal,
                "country": "CA",
                "province": "ON",
                "city": "London",
                "address1": "1 Main St",
            },
            "items": [_item(1, (20, 20, 20))],
        }
    }
    body = json.dumps(payload).encode()
    secret = "shpss_test"
    shop = SimpleNamespace(
        id="s1", merchant_id=merchant.id, shop_domain="kaylulu.myshopify.com", encrypted_webhook_secret=None
    )
    db = MagicMock()
    db.get.return_value = merchant
    pickup = SimpleNamespace(formatted="Milton", postal="L9T2X5", lat=43.52, lng=-79.88, place_id=None)
    breakdown = {"final_cents": quote_return[0], "metadata": {"pricing_model": "contract_route"}}
    quote = MagicMock(return_value=(quote_return[0], breakdown))
    with (
        patch("porterchain_api.integrations.shopify_carrier_rates._active_shop", return_value=shop),
        patch(
            "porterchain_api.integrations.shopify_carrier_rates.default_pickup_address",
            return_value=pickup,
        ),
        patch(
            "porterchain_api.integrations.shopify_carrier_rates.address_from_saved",
            side_effect=lambda row: AddressInput(
                formatted=row.formatted, postal=row.postal, lat=row.lat, lng=row.lng
            ),
        ),
        patch("porterchain_api.integrations.shopify_carrier_rates._ensure_geo", side_effect=lambda a: a),
        patch("porterchain_api.integrations.shopify_carrier_rates.quote_merchant_rate", quote),
    ):
        out = carrier_service_rates(
            db,
            SimpleNamespace(shopify_api_secret=secret, jwt_secret="x" * 32),
            raw_body=body,
            hmac_header=base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode(),
            shop_domain="kaylulu.myshopify.com",
            payload=payload,
        )
    return out, quote


def test_shopify_checkout_quotes_a_registry_gap_fsa_for_kaylulu():
    out, quote = _carrier(_kaylulu(), "N6H1A1")
    assert quote.called
    assert out["rates"] and out["rates"][0]["total_price"] == "28250"


def test_shopify_checkout_still_refuses_out_of_tile_for_distance_merchants():
    out, quote = _carrier(_kaylulu(pricing_model="distance"), "N6H1A1")
    assert out == {"rates": []}
    assert not quote.called


def _engine_quote(merchant, dest: str, items: list[dict]):
    ctx = PricingContext(merchant_policy=policy_from_config(merchant.pricing_config))
    ctx.merchant_policy.pricing_model = merchant.pricing_model
    svc = SimpleNamespace(calculate_merchant=lambda req: PricingEngine().calculate(req, ctx))
    with (
        patch(
            "porterchain_api.integrations.shopify_carrier_rates.resolve_route_distance",
            return_value=(60000, 3600, "test"),
        ),
        patch("porterchain_api.integrations.shopify_carrier_rates.get_pricing_service", return_value=svc),
    ):
        return quote_merchant_rate(
            MagicMock(), merchant, pickup=_addr("L9T"), dropoff=_addr(dest), weight_kg=None, items=items
        )


def test_shopify_quote_bills_each_unit_as_a_van_stop():
    cents, meta = _engine_quote(_kaylulu(), "L8P", [_item(5, (20, 20, 20), grams=5000)])
    assert meta["subtotal_cents"] == 26500  # 40 pickup + 5 × T2 45
    assert meta["metadata"]["contract_vehicle"] == "cargo_van"


def test_shopify_quote_small_parcels_in_territory_go_compact():
    merchant = _kaylulu()
    items = [_item(3, (8, 8, 8))]
    assert resolve_shopify_vehicle(merchant, dropoff=_addr("L5M"), items=items) == "sedan_suv"
    _cents, meta = _engine_quote(merchant, "L5M", items)
    assert meta["subtotal_cents"] == 5000
    assert meta["metadata"]["contract_vehicle"] == "compact"


def test_shopify_vehicle_is_van_outside_territory_or_without_sizes():
    merchant = _kaylulu()
    assert resolve_shopify_vehicle(merchant, dropoff=_addr("N6A"), items=[_item(1, (8, 8, 8))]) == "cargo_van"
    assert resolve_shopify_vehicle(merchant, dropoff=_addr("L5M"), items=[_item(1, None)]) == "cargo_van"
    mixed = [_item(1, (8, 8, 8)), _item(1, (12, 10, 4))]
    assert resolve_shopify_vehicle(merchant, dropoff=_addr("L5M"), items=mixed) == "cargo_van"


def test_shopify_handling_tier_on_heavy_unit():
    heavy = _item(1, (85, 45, 20), grams=36000)  # size Tier 2
    _cents, meta = _engine_quote(_kaylulu(), "N6A", [heavy])
    assert meta["subtotal_cents"] == 25000  # 40 + 60 + 60 → T3 minimum 250
    assert sum(i["amount_cents"] for i in meta["items"] if i["code"] == "handling") == 6000


def test_parcels_from_items_one_per_unit():
    parcels = parcels_from_items([_item(2, (10, 10, 10), grams=1500), {"quantity": 1, "requires_shipping": False}])
    assert len(parcels) == 2
    assert parcels[0].weight_kg == 1.5
    assert parcels[0].dimensions == {"length": 25.4, "width": 25.4, "height": 25.4}


def test_booking_packages_become_priced_parcels_on_single_drop():
    body = MerchantBookDeliveryRequest(
        pickup=_addr("L9T"),
        dropoff=_addr("L8P"),
        scheduled_at=datetime.now(UTC),
        packages=[
            RouteImportPackageInput(weight_kg=60, length_cm=210, width_cm=110, height_cm=50),
            RouteImportPackageInput(dimensions="20x20x20"),
        ],
    )
    parcels = parcels_for_pricing(body)
    assert [p.weight_kg for p in parcels] == [60.0, None]
    assert parcels[0].dimensions == {"length": 210.0, "width": 110.0, "height": 50.0}
    multi = body.model_copy(update={"additional_stops": [_addr("N2G")]})
    assert parcels_for_pricing(multi) == []


# ── admin FSA editor ────────────────────────────────────────────────────


_GET_MERCHANT = "porterchain_api.admin_engine.merchant_service.AdminMerchantService.get_merchant"


def test_admin_fsa_editor_allows_out_of_tile_rows_for_fsa_merchants_only():
    svc = FsaAdminService()
    db = MagicMock()
    with patch(_GET_MERCHANT, return_value=SimpleNamespace(pricing_model="fsa")):
        assert svc.dest_tile_required(db, "kay") is False
        assert svc.dest_tile_required(db, None) is True
    with patch(_GET_MERCHANT, return_value=SimpleNamespace(pricing_model="distance")):
        assert svc.dest_tile_required(db, "dist") is True
    with patch(_GET_MERCHANT, return_value=None):
        assert svc.dest_tile_required(db, "missing") is True
    assert svc.validated_fsa("N6H", field="dest_fsa", required=True, require_in_tile=False) == "N6H"
    with pytest.raises(ValueError, match="outside_ontario"):
        svc.validated_fsa("H2X", field="dest_fsa", required=True, require_in_tile=False)


def test_admin_bulk_upsert_fsa_merchant_rows_beyond_tile():
    svc = FsaAdminService()
    db = MagicMock()
    q = MagicMock()
    db.query.return_value = q
    q.filter.return_value = q
    q.first.return_value = None
    rows = [FsaRateBody(dest_fsa=f, flat_cents=6000) for f in ("N6H", "L3W", "H2X")]
    with patch(_GET_MERCHANT, return_value=SimpleNamespace(pricing_model="fsa")):
        result = svc.bulk_upsert(db, rows, merchant_id="kay")
        platform = svc.bulk_upsert(db, [FsaRateBody(dest_fsa="N6H", flat_cents=6000)], merchant_id=None)
    assert result["created"] == 2
    assert result["error_count"] == 1
    assert "out_of_gta150_tile" in platform["errors"][0]["error"]


# ── template ────────────────────────────────────────────────────────────


def test_template_points_at_the_contract_schedule():
    cfg = kaylulu_pricing_config(existing={"custom_rules": {"keep": True}})
    assert cfg["custom_rules"] == {"keep": True}
    assert cfg["schedule"]["contract_schedule"] == "kaylulu-2026-09"
    assert cfg["schedule"]["size_match"] == "all"
    assert cfg["surcharges"] == {"downtown": False, "upper_zone": False}
    assert cfg["schedule"]["route_minimums_cents"] == {"T1": 12000, "T2": 20000, "T3": 25000}
