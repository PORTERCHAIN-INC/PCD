"""Shopify carrier handshake: engine pricing + HMAC security (dummy fixtures)."""

from __future__ import annotations

import base64
import hashlib
import hmac
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.integrations.shopify_carrier_rates import (
    carrier_service_rates,
    quote_merchant_rate,
)


def _hmac(body: bytes, secret: str) -> str:
    return base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()


def _settings(*, secret: str = "shpss_test") -> SimpleNamespace:
    return SimpleNamespace(shopify_api_secret=secret, jwt_secret="test-jwt-secret-key-32chars!!")


def _payload(*, currency: str = "CAD", destination_postal: str = "M5V1A1") -> dict:
    return {
        "rate": {
            "currency": currency,
            "origin": {"postal_code": "M5V1A1", "country": "CA", "province": "ON"},
            "destination": {
                "postal_code": destination_postal,
                "country": "CA",
                "province": "ON",
                "city": "Toronto",
                "address1": "100 Queen St W",
            },
            "items": [{"name": "Box", "quantity": 1, "grams": 2000}],
        }
    }


def _active_merchant(**overrides):
    base = dict(
        id="m1",
        status=MerchantStatus.ACTIVE.value,
        encrypted_webhook_secret=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_two_merchants_different_engine_prices():
    """Same Shopify rate shape → different cents via shop→merchant + engine."""
    db = MagicMock()
    settings = _settings()
    body = b'{"rate":{"currency":"CAD"}}'
    header = _hmac(body, settings.shopify_api_secret)

    shop_a = SimpleNamespace(
        id="s-a",
        merchant_id="merchant-a",
        shop_domain="alpha.myshopify.com",
        encrypted_webhook_secret=None,
    )
    shop_b = SimpleNamespace(
        id="s-b",
        merchant_id="merchant-b",
        shop_domain="beta.myshopify.com",
        encrypted_webhook_secret=None,
    )
    merchant_a = _active_merchant(id="merchant-a")
    merchant_b = _active_merchant(id="merchant-b")

    def get_merchant(model, mid):  # noqa: ARG001
        return merchant_a if mid == "merchant-a" else merchant_b

    db.get.side_effect = get_merchant
    pickup = SimpleNamespace(
        formatted="1 King St W, Toronto",
        postal="M5V1A1",
        lat=43.65,
        lng=-79.38,
        place_id=None,
    )

    with (
        patch(
            "porterchain_api.integrations.shopify_carrier_rates._active_shop",
            side_effect=lambda _db, domain: shop_a if "alpha" in (domain or "") else shop_b,
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
            side_effect=lambda _db, merchant, **_kw: (
                (6100, {"final_cents": 6100})
                if merchant.id == "merchant-a"
                else (8900, {"final_cents": 8900})
            ),
        ),
        patch(
            "porterchain_api.integrations.shopify_carrier_rates.persist_rate_quote",
            side_effect=lambda *_a, **_kw: SimpleNamespace(id="quote-1"),
        ),
    ):
        out_a = carrier_service_rates(
            db,
            settings,
            raw_body=body,
            hmac_header=header,
            shop_domain="alpha.myshopify.com",
            payload=_payload(),
        )
        out_b = carrier_service_rates(
            db,
            settings,
            raw_body=body,
            hmac_header=header,
            shop_domain="beta.myshopify.com",
            payload=_payload(),
        )

    assert out_a["rates"][0]["total_price"] == "6100"
    assert out_b["rates"][0]["total_price"] == "8900"
    assert out_a["rates"][0]["service_code"] == "porterchain_same_day"


def test_destination_affects_quote_call():
    """Engine is invoked with dropoff from Shopify destination (not ignored)."""
    db = MagicMock()
    settings = _settings()
    shop = SimpleNamespace(id="s1", merchant_id="m1", encrypted_webhook_secret=None)
    merchant = _active_merchant()
    db.get.return_value = merchant
    pickup = SimpleNamespace(
        formatted="1 King", postal="M5V1A1", lat=43.65, lng=-79.38, place_id=None
    )
    seen: list[str] = []

    def fake_quote(_db, _merchant, *, pickup, dropoff, weight_kg):  # noqa: ARG001
        seen.append(dropoff.postal or "")
        return 5200, {"final_cents": 5200}

    body_near = b'{"near":1}'
    body_far = b'{"far":1}'

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
            side_effect=fake_quote,
        ),
        patch(
            "porterchain_api.integrations.shopify_carrier_rates.persist_rate_quote",
            return_value=SimpleNamespace(id="q1"),
        ),
    ):
        carrier_service_rates(
            db,
            settings,
            raw_body=body_near,
            hmac_header=_hmac(body_near, settings.shopify_api_secret),
            shop_domain="acme.myshopify.com",
            payload=_payload(destination_postal="M5V1A1"),
        )
        carrier_service_rates(
            db,
            settings,
            raw_body=body_far,
            hmac_header=_hmac(body_far, settings.shopify_api_secret),
            shop_domain="acme.myshopify.com",
            payload=_payload(destination_postal="L6A1A1"),
        )

    assert seen == ["M5V1A1", "L6A1A1"]


def test_out_of_area_returns_empty_rates():
    db = MagicMock()
    settings = _settings()
    shop = SimpleNamespace(
        id="s1", merchant_id="m1", shop_domain="acme.myshopify.com", encrypted_webhook_secret=None
    )
    merchant = _active_merchant()
    db.get.return_value = merchant
    pickup = SimpleNamespace(
        formatted="1 King", postal="M5V1A1", lat=43.65, lng=-79.38, place_id=None
    )
    body = b"{}"

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
            return_value="destination is outside Ontario",
        ),
    ):
        out = carrier_service_rates(
            db,
            settings,
            raw_body=body,
            hmac_header=_hmac(body, settings.shopify_api_secret),
            shop_domain="acme.myshopify.com",
            payload=_payload(destination_postal="H2X1Y1"),
        )
    assert out == {"rates": []}


def test_inactive_merchant_empty_rates():
    db = MagicMock()
    settings = _settings()
    shop = SimpleNamespace(
        id="s1", merchant_id="m1", shop_domain="acme.myshopify.com", encrypted_webhook_secret=None
    )
    db.get.return_value = _active_merchant(status="ONBOARDING")
    body = b"{}"

    with patch(
        "porterchain_api.integrations.shopify_carrier_rates._active_shop",
        return_value=shop,
    ):
        out = carrier_service_rates(
            db,
            settings,
            raw_body=body,
            hmac_header=_hmac(body, settings.shopify_api_secret),
            shop_domain="acme.myshopify.com",
            payload=_payload(),
        )
    assert out == {"rates": []}


def test_no_pickup_empty_rates():
    db = MagicMock()
    settings = _settings()
    shop = SimpleNamespace(
        id="s1", merchant_id="m1", shop_domain="acme.myshopify.com", encrypted_webhook_secret=None
    )
    db.get.return_value = _active_merchant()
    body = b"{}"

    with (
        patch(
            "porterchain_api.integrations.shopify_carrier_rates._active_shop",
            return_value=shop,
        ),
        patch(
            "porterchain_api.integrations.shopify_carrier_rates.default_pickup_address",
            return_value=None,
        ),
    ):
        out = carrier_service_rates(
            db,
            settings,
            raw_body=body,
            hmac_header=_hmac(body, settings.shopify_api_secret),
            shop_domain="acme.myshopify.com",
            payload=_payload(),
        )
    assert out == {"rates": []}


def test_invalid_hmac_rejected():
    db = MagicMock()
    settings = _settings()
    shop = SimpleNamespace(merchant_id="m1", encrypted_webhook_secret=None)
    with patch(
        "porterchain_api.integrations.shopify_carrier_rates._active_shop",
        return_value=shop,
    ):
        with pytest.raises(PermissionError, match="invalid_hmac"):
            carrier_service_rates(
                db,
                settings,
                raw_body=b'{"rate":{}}',
                hmac_header="not-a-valid-hmac",
                shop_domain="acme.myshopify.com",
                payload=_payload(),
            )


def test_missing_hmac_rejected_when_secret_configured():
    db = MagicMock()
    settings = _settings()
    shop = SimpleNamespace(merchant_id="m1", encrypted_webhook_secret=None)
    with patch(
        "porterchain_api.integrations.shopify_carrier_rates._active_shop",
        return_value=shop,
    ):
        with pytest.raises(PermissionError, match="invalid_hmac"):
            carrier_service_rates(
                db,
                settings,
                raw_body=b'{"rate":{}}',
                hmac_header=None,
                shop_domain="acme.myshopify.com",
                payload=_payload(),
            )


def test_hmac_not_configured_rejected():
    db = MagicMock()
    settings = _settings(secret="")
    shop = SimpleNamespace(merchant_id="m1", encrypted_webhook_secret=None)
    with patch(
        "porterchain_api.integrations.shopify_carrier_rates._active_shop",
        return_value=shop,
    ):
        with pytest.raises(PermissionError, match="hmac_not_configured"):
            carrier_service_rates(
                db,
                settings,
                raw_body=b"{}",
                hmac_header=None,
                shop_domain="acme.myshopify.com",
                payload=_payload(),
            )


def test_shop_webhook_secret_accepted_without_app_secret():
    db = MagicMock()
    settings = _settings(secret="")
    shop_secret = "shpss_shop_only"
    shop = SimpleNamespace(
        id="s1",
        merchant_id="m1",
        encrypted_webhook_secret="enc:shop",
    )
    merchant = _active_merchant()
    db.get.return_value = merchant
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
            "porterchain_api.integrations.shopify_carrier_rates._decrypt",
            return_value=shop_secret,
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
            return_value=(4100, {"final_cents": 4100}),
        ),
        patch(
            "porterchain_api.integrations.shopify_carrier_rates.persist_rate_quote",
            return_value=SimpleNamespace(id="q"),
        ),
    ):
        out = carrier_service_rates(
            db,
            settings,
            raw_body=body,
            hmac_header=_hmac(body, shop_secret),
            shop_domain="custom.myshopify.com",
            payload=_payload(),
        )
    assert out["rates"][0]["total_price"] == "4100"


def test_spoofed_shop_cannot_use_other_merchant_secret():
    db = MagicMock()
    settings = _settings(secret="")
    shop = SimpleNamespace(merchant_id="victim", encrypted_webhook_secret="enc")
    body = b'{"rate":{}}'
    attacker_header = _hmac(body, "attacker_secret")

    with (
        patch(
            "porterchain_api.integrations.shopify_carrier_rates._active_shop",
            return_value=shop,
        ),
        patch(
            "porterchain_api.integrations.shopify_carrier_rates._decrypt",
            return_value="victim_shop_secret",
        ),
    ):
        with pytest.raises(PermissionError, match="invalid_hmac"):
            carrier_service_rates(
                db,
                settings,
                raw_body=body,
                hmac_header=attacker_header,
                shop_domain="victim.myshopify.com",
                payload=_payload(),
            )


def test_unknown_shop_rejected_after_hmac():
    db = MagicMock()
    settings = _settings()
    body = b'{"rate":{}}'
    with patch(
        "porterchain_api.integrations.shopify_carrier_rates._active_shop",
        return_value=None,
    ):
        with pytest.raises(LookupError, match="shop_not_connected"):
            carrier_service_rates(
                db,
                settings,
                raw_body=body,
                hmac_header=_hmac(body, settings.shopify_api_secret),
                shop_domain="ghost.myshopify.com",
                payload=_payload(),
            )


def test_quote_merchant_rate_calls_pricing_service():
    db = MagicMock()
    merchant = _active_merchant()
    pickup = SimpleNamespace(formatted="a", postal="M5V1A1", lat=43.65, lng=-79.38)
    dropoff = SimpleNamespace(formatted="b", postal="M2N1A1", lat=43.7, lng=-79.4)
    breakdown = SimpleNamespace(
        final_cents=7777,
        subtotal_cents=7000,
        tax_cents=777,
        contract_id=None,
        items=[],
        metadata={},
    )
    svc = MagicMock()
    svc.calculate_merchant.return_value = breakdown

    with (
        patch(
            "porterchain_api.integrations.shopify_carrier_rates.resolve_route_distance",
            return_value=(12000, 900, "valhalla"),
        ),
        patch(
            "porterchain_api.integrations.shopify_carrier_rates.get_pricing_service",
            return_value=svc,
        ),
    ):
        cents, meta = quote_merchant_rate(
            db,
            merchant,
            pickup=pickup,  # type: ignore[arg-type]
            dropoff=dropoff,  # type: ignore[arg-type]
            weight_kg=2.0,
        )
    assert cents == 7777
    assert meta["final_cents"] == 7777
    assert svc.calculate_merchant.called
    req = svc.calculate_merchant.call_args[0][0]
    assert req.merchant_id == "m1"
    assert req.channel == "merchant"
    assert req.distance_meters == 12000
