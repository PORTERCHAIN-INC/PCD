"""App review 139170: no JSON dead ends, out-of-area = empty 200, carrier re-heal."""

from __future__ import annotations

import base64
import hashlib
import hmac
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from porterchain_api.config import Settings, get_settings
from porterchain_api.integrations.shopify_carrier_rates import carrier_service_rates
from porterchain_api.merchant_engine import shopify_service as shopify
from porterchain_api.merchant_engine.shopify_fulfillment_ops import carrier_error_code
from porterchain_api.routers import shopify as shopify_router

_GQL = "porterchain_api.merchant_engine.shopify_admin_graphql"


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="local",
        stripe_mock=True,
        jwt_secret="test-jwt-secret-key-32chars!!",
        porterchain_api_url="https://api.porterchain.com",
        merchant_portal_url="https://merchant.porterchain.com",
        shopify_api_key="cid",
        shopify_api_secret="shpss_test",
        fleetbase_dispatch_bridge=False,
        spicedb_enabled=False,
        spicedb_use_memory=True,
        spicedb_required=False,
    )


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(shopify_router.router)
    app.dependency_overrides[get_settings] = _settings
    return TestClient(app, follow_redirects=False)


def test_legacy_callback_redirects_into_shopify_admin_not_json() -> None:
    res = _client().get(
        "/v1/integrations/shopify/callback?code=abc&shop=qhrk0d-5s.myshopify.com"
    )
    assert res.status_code == 302
    assert (
        res.headers["location"] == "https://admin.shopify.com/store/qhrk0d-5s/apps/cid"
    )


def test_legacy_install_redirects_into_shopify_admin() -> None:
    res = _client().get("/v1/integrations/shopify/install?shop=qhrk0d-5s.myshopify.com")
    assert res.status_code == 302
    assert "admin.shopify.com/store/qhrk0d-5s/apps/cid" in res.headers["location"]


def test_legacy_callback_without_shop_is_friendly_html() -> None:
    res = _client().get("/v1/integrations/shopify/callback?code=abc")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/html")
    assert "Shopify admin" in res.text
    assert '"detail"' not in res.text


def _signed(body: bytes) -> str:
    return base64.b64encode(
        hmac.new(b"shpss_test", body, hashlib.sha256).digest()
    ).decode()


def test_philippines_destination_gets_empty_rates_not_error() -> None:
    body = b'{"rate":{}}'
    shop = SimpleNamespace(
        id="s1", shop_domain="qhrk0d-5s.myshopify.com", merchant_id="m1", encrypted_webhook_secret=None
    )
    db = MagicMock()
    db.get.return_value = SimpleNamespace(id="m1", status="active", encrypted_webhook_secret=None)
    payload = {
        "rate": {
            "currency": "PHP",
            "origin": {"country": "PH", "postal_code": "1000"},
            "destination": {"country": "PH", "postal_code": "1000", "city": "Manila"},
            "items": [{"name": "Box", "quantity": 1, "grams": 500}],
        }
    }
    with patch(
        "porterchain_api.integrations.shopify_carrier_rates._active_shop",
        return_value=shop,
    ):
        result = carrier_service_rates(
            db,
            SimpleNamespace(shopify_api_secret="shpss_test", jwt_secret="x" * 32),
            raw_body=body,
            hmac_header=_signed(body),
            shop_domain=shop.shop_domain,
            payload=payload,
        )
    assert result == {"rates": []}


def test_ccs_not_enabled_message_maps_to_plan_unsupported() -> None:
    msg = "Carrier Calculated Shipping must be enabled for your store before enabling: PorterChain"
    assert carrier_error_code(msg) == "carrier_plan_unsupported"


def test_open_app_reregisters_when_service_deleted_on_store(db) -> None:
    from porterchain_api.merchant_engine.shopify_session import ensure_carrier_rates
    from tests.test_shopify_app_review import _company, _shop

    settings = _settings()
    ctx = _company(db)
    shop = _shop(
        db,
        ctx.id,
        token=shopify._encrypt("tok", settings),
        gid="gid://shopify/DeliveryCarrierService/1",
    )
    with (
        patch(f"{_GQL}.carrier_service_find", return_value=None),
        patch(
            f"{_GQL}.carrier_service_create",
            return_value="gid://shopify/DeliveryCarrierService/2",
        ) as create,
    ):
        assert ensure_carrier_rates(db, settings, shop.shop_domain) == "ready"
    create.assert_called_once()
    db.refresh(shop)
    assert shop.carrier_service_gid == "gid://shopify/DeliveryCarrierService/2"


def test_open_app_keeps_present_service_without_recreating(db) -> None:
    from porterchain_api.merchant_engine.shopify_session import ensure_carrier_rates
    from tests.test_shopify_app_review import _company, _shop

    settings = _settings()
    ctx = _company(db)
    shop = _shop(
        db,
        ctx.id,
        token=shopify._encrypt("tok", settings),
        gid="gid://shopify/DeliveryCarrierService/1",
    )
    with (
        patch(
            f"{_GQL}.carrier_service_find",
            return_value="gid://shopify/DeliveryCarrierService/1",
        ),
        patch(f"{_GQL}.carrier_service_create") as create,
    ):
        assert ensure_carrier_rates(db, settings, shop.shop_domain) == "ready"
    create.assert_not_called()


def test_open_with_stored_carrier_answers_fast_and_verifies_in_background(db) -> None:
    from tests.test_shopify_app_review import _company, _shop

    from porterchain_api.merchant_engine import shopify_session as sess

    settings = _settings()
    ctx = _company(db)
    shop = _shop(db, ctx.id, token=shopify._encrypt("tok", settings), gid="gid://shopify/DeliveryCarrierService/1")
    queued: list = []
    with (
        patch.object(sess, "verify_session_token", return_value=shop.shop_domain),
        patch("porterchain_api.merchant_engine.shopify_tokens.token_state_for_open", return_value="ok"),
        patch(f"{_GQL}.carrier_service_find") as find,
    ):
        out = sess.open_embedded(db, settings, "tok", defer=queued.append)
    assert out["rates"] == "ready"
    find.assert_not_called()  # no Shopify round-trip before the page renders
    assert len(queued) == 1
