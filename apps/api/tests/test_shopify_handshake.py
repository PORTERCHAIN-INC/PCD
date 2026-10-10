"""Shopify delivery handshake: carrier contract, book filter, event mirror."""

from __future__ import annotations

import base64
import hashlib
import hmac
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.integrations.shopify_carrier_rates import carrier_service_rates
from porterchain_api.integrations.shopify_orders import (
    customer_slice,
    porterchain_shipping_selected,
    unpaid_non_cod,
)
from porterchain_api.merchant_engine.shopify_fulfillment_service import (
    _order_payload_from_fo,
    _reject_reason,
    fulfillment_event_status,
)


def _hmac(body: bytes, secret: str) -> str:
    return base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()


def test_shipping_line_filter_and_unpaid() -> None:
    assert porterchain_shipping_selected({"id": "1"}) is True
    assert porterchain_shipping_selected({"shipping_lines": [{"code": "canada_post"}]}) is False
    assert (
        porterchain_shipping_selected(
            {"shipping_lines": [{"code": "porterchain_same_day", "title": "PorterChain Same Day"}]}
        )
        is True
    )
    assert unpaid_non_cod({}) is False
    assert unpaid_non_cod({"financial_status": "paid"}) is False
    assert unpaid_non_cod({"financial_status": "pending"}) is True
    assert (
        unpaid_non_cod(
            {"financial_status": "pending", "payment_gateway_names": ["Cash on Delivery (COD)"]}
        )
        is False
    )


def test_customer_slice_is_delivery_only() -> None:
    slice_ = customer_slice(
        {
            "email": "buyer@example.com",
            "shipping_address": {"name": "Ada", "phone": "4165550100"},
            "customer": {"id": 9, "email": "buyer@example.com"},
        }
    )
    assert slice_["email"] == "buyer@example.com"
    assert slice_["phone"] == "4165550100"
    assert "marketing" not in slice_


def test_reject_outside_tile_and_local_without_our_rate() -> None:
    ottawa = {
        "shipping_address": {"zip": "K1A0A6", "country": "CA"},
        "shipping_lines": [{"code": "porterchain_same_day"}],
    }
    assert _reject_reason(ottawa, "SHIPPING") == "Outside the priced delivery tile."
    local = {
        "shipping_address": {"zip": "M5V1A1", "country": "CA"},
        "shipping_lines": [{"code": "shopify_local"}],
    }
    assert _reject_reason(local, "LOCAL") == "Local delivery is not a PorterChain rate."
    ours = {
        "shipping_address": {"zip": "M5V1A1", "country": "CA"},
        "shipping_lines": [{"code": "porterchain_same_day"}],
    }
    assert _reject_reason(ours, "LOCAL") is None
    assert _reject_reason(ours, "PICK_UP") == "PorterChain delivers shipping orders only."


def test_fo_payload_keeps_real_shipping_lines() -> None:
    payload = _order_payload_from_fo(
        {
            "id": "gid://shopify/FulfillmentOrder/1",
            "deliveryMethod": {"methodType": "LOCAL"},
            "destination": {"zip": "M5V1A1", "countryCode": "CA", "address1": "1 King"},
            "order": {
                "legacyResourceId": "55",
                "name": "#55",
                "shippingLines": {"edges": [{"node": {"code": "shopify_local", "title": "Local"}}]},
            },
        }
    )
    assert payload["shipping_lines"][0]["code"] == "shopify_local"
    assert payload["id"] == "55"


def test_event_status_mirror() -> None:
    assert fulfillment_event_status("PICKED_UP") == "CARRIER_PICKED_UP"
    assert fulfillment_event_status("AT_DESTINATION") == "OUT_FOR_DELIVERY"
    assert fulfillment_event_status("DELIVERED") == "DELIVERED"
    assert fulfillment_event_status("IN_TRANSIT", "order.delayed") == "DELAYED"
    assert fulfillment_event_status("IN_TRANSIT", "exception.opened") == "ATTEMPTED_DELIVERY"
    assert fulfillment_event_status("FAILED") == "FAILURE"


def _rate_call(payload: dict) -> dict:
    db = MagicMock()
    shop = SimpleNamespace(id="s1", merchant_id="m1", encrypted_webhook_secret=None)
    merchant = SimpleNamespace(id="m1", status=MerchantStatus.ACTIVE.value)
    db.get.return_value = merchant
    settings = SimpleNamespace(shopify_api_secret="shpss_test", jwt_secret="x" * 32)
    body = b"{}"
    pickup = SimpleNamespace(formatted="1 King", postal="M5V1A1", lat=43.65, lng=-79.38, place_id=None)
    with (
        patch(
            "porterchain_api.integrations.shopify_carrier_rates._active_shop",
            return_value=shop,
        ),
        patch(
            "porterchain_api.integrations.shopify_carrier_rates.default_pickup_address",
            return_value=pickup,
        ),
        patch(
            "porterchain_api.integrations.shopify_carrier_rates.address_from_saved",
            side_effect=lambda row: SimpleNamespace(
                formatted=row.formatted,
                postal=row.postal,
                lat=row.lat,
                lng=row.lng,
                place_id=None,
            ),
        ),
        patch(
            "porterchain_api.integrations.shopify_carrier_rates._ensure_geo",
            side_effect=lambda a: a if hasattr(a, "lat") and a.lat is not None else (a.model_copy(update={"lat": 43.65, "lng": -79.38}) if hasattr(a, "model_copy") else a),
        ),
        patch(
            "porterchain_api.integrations.shopify_carrier_rates.quote_merchant_rate",
            return_value=(5200, {"final_cents": 5200}),
        ),
        patch(
            "porterchain_api.integrations.shopify_carrier_rates.persist_rate_quote",
            return_value=SimpleNamespace(id="quote-xyz"),
        ),
    ):
        return carrier_service_rates(
            db,
            settings,
            raw_body=body,
            hmac_header=_hmac(body, settings.shopify_api_secret),
            shop_domain="acme.myshopify.com",
            payload=payload,
        )


def test_carrier_contract_and_empty_outside_tile() -> None:
    priced = _rate_call(
        {
            "rate": {
                "currency": "CAD",
                "origin": {
                    "postal_code": "M5V1A1",
                    "country": "CA",
                    "city": "Toronto",
                    "address1": "1 King",
                },
                "destination": {
                    "postal_code": "M5V1A1",
                    "country": "CA",
                    "province": "ON",
                    "city": "Toronto",
                    "address1": "100 Queen",
                },
                "items": [{"grams": 1000, "quantity": 1}],
            }
        }
    )
    rate = priced["rates"][0]
    assert rate["service_code"] == "porterchain_same_day"
    assert rate["phone_required"] is True
    assert rate["metafields"][0]["key"] == "quote_id"
    assert rate["metafields"][0]["value"] == "quote-xyz"
    assert "quote" not in rate["service_code"]
    assert rate["min_delivery_date"]
    assert rate["max_delivery_date"]

    ottawa = _rate_call(
        {
            "rate": {
                "currency": "CAD",
                "destination": {
                    "postal_code": "K1A0A6",
                    "country": "CA",
                    "province": "ON",
                    "city": "Ottawa",
                    "address1": "1 Wellington",
                },
            }
        }
    )
    assert ottawa == {"rates": []}

    vancouver = _rate_call(
        {
            "rate": {
                "currency": "CAD",
                "destination": {
                    "postal_code": "V6B1A1",
                    "country": "CA",
                    "province": "BC",
                    "city": "Vancouver",
                    "address1": "1 Robson",
                },
            }
        }
    )
    assert vancouver == {"rates": []}

    united_states = _rate_call(
        {
            "rate": {
                "currency": "CAD",
                "destination": {"postal_code": "10001", "country": "US", "city": "New York"},
            }
        }
    )
    assert united_states == {"rates": []}
