"""P4.4 Shopify carrier rates — thin unit test."""

from __future__ import annotations

import base64
import hashlib
import hmac
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.integrations.shopify_carrier_rates import carrier_service_rates


def _hmac(body: bytes, secret: str) -> str:
    return base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()


def test_carrier_service_rates_returns_same_day():
    db = MagicMock()
    shop = SimpleNamespace(id="s1", merchant_id="m1", encrypted_webhook_secret=None)
    merchant = SimpleNamespace(id="m1", status=MerchantStatus.ACTIVE.value)
    db.get.return_value = merchant
    settings = SimpleNamespace(shopify_api_secret="shpss_test", jwt_secret="x" * 32)
    body = b'{"rate":{"currency":"CAD"}}'
    pickup = SimpleNamespace(
        formatted="1 King", postal="M5V1A1", lat=43.65, lng=-79.38, place_id=None
    )

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
            "porterchain_api.integrations.shopify_carrier_rates.service_area_error",
            return_value=None,
        ),
        patch(
            "porterchain_api.integrations.shopify_carrier_rates._ensure_geo",
            side_effect=lambda a: a,
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
        out = carrier_service_rates(
            db,
            settings,
            raw_body=body,
            hmac_header=_hmac(body, settings.shopify_api_secret),
            shop_domain="acme.myshopify.com",
            payload={
                "rate": {
                    "currency": "CAD",
                    "destination": {
                        "postal_code": "M5V1A1",
                        "country": "CA",
                        "province": "ON",
                        "city": "Toronto",
                        "address1": "100 Queen",
                    },
                    "items": [{"grams": 1000, "quantity": 1}],
                }
            },
        )
    assert out["rates"][0]["service_code"] == "porterchain_same_day"
    assert out["rates"][0]["total_price"] == "5200"
    assert out["rates"][0]["currency"] == "CAD"
