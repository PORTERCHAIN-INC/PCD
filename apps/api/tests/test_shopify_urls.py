"""Shopify Partner App URL helpers."""

from __future__ import annotations

import tomllib
from pathlib import Path

from porterchain_api.config import Settings
from porterchain_api.merchant_engine import shopify_service as shopify

_REPO_ROOT = Path(__file__).resolve().parents[3]
_APP_TOML = _REPO_ROOT / "integrations" / "shopify" / "app.toml"


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
    )


def test_partner_app_urls() -> None:
    settings = _settings()
    assert shopify.oauth_configured(settings) is True
    assert shopify.webhook_url(settings).endswith("/v1/integrations/shopify/webhooks")
    assert shopify.callback_url(settings).endswith("/v1/integrations/shopify/callback")
    assert shopify.carrier_rates_url(settings).endswith(
        "/v1/integrations/shopify/carrier-service/rates"
    )
    assert shopify.fulfillment_service_url(settings).endswith(
        "/v1/integrations/shopify/fulfillment-order-notification"
    )
    assert shopify.app_home_url(settings) == "https://merchant.porterchain.com/shopify"
    assert (
        shopify.app_home_url(settings, shop_domain="Acme.myshopify.com")
        == "https://merchant.porterchain.com/shopify?shop=acme.myshopify.com&connected=1"
    )


def test_oauth_state_roundtrip_with_pickup() -> None:
    settings = _settings()
    token = shopify.sign_oauth_state(
        "merchant-1", settings, pickup_address_id="addr-9"
    )
    state = shopify.read_oauth_state(token, settings)
    assert state.merchant_id == "merchant-1"
    assert state.pickup_address_id == "addr-9"


def test_install_url_embeds_pickup_in_state() -> None:
    settings = _settings()
    url = shopify.install_url(
        "demo.myshopify.com",
        settings,
        merchant_id="m-1",
        pickup_address_id="pickup-1",
    )
    assert "client_id=cid" in url
    assert "scope=" in url
    from urllib.parse import parse_qs, urlparse

    qs = parse_qs(urlparse(url).query)
    state = shopify.read_oauth_state(qs["state"][0], settings)
    assert state.merchant_id == "m-1"
    assert state.pickup_address_id == "pickup-1"



def test_app_toml_matches_runtime_defaults() -> None:
    """Partners stub must track API defaults; client_id stays empty until publish."""
    settings = _settings()
    raw = tomllib.loads(_APP_TOML.read_text(encoding="utf-8"))

    assert raw.get("client_id") == ""
    assert raw["application_url"] == shopify.app_home_url(settings)
    assert raw["access_scopes"]["scopes"] == settings.shopify_api_scopes
    assert raw["webhooks"]["api_version"] == settings.shopify_api_version
    assert settings.shopify_api_version == "2026-07"

    subs = raw["webhooks"]["subscriptions"]
    topics: set[str] = set()
    compliance: set[str] = set()
    for sub in subs:
        assert sub["uri"] == shopify.webhook_url(settings)
        topics.update(sub.get("topics") or [])
        compliance.update(sub.get("compliance_topics") or [])

    assert {"orders/create", "orders/cancelled", "app/uninstalled"} <= topics
    assert {"customers/data_request", "customers/redact", "shop/redact"} <= compliance
    # FO topics only when SHOPIFY_FULFILLMENT_SERVICE_ENABLED (default off).
    assert "fulfillment_orders/fulfillment_request_submitted" not in topics
