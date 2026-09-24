"""Shopify Partner App URL helpers."""

from porterchain_api.config import Settings
from porterchain_api.merchant_engine import shopify_service as shopify


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


def test_default_scopes_include_shipping() -> None:
    settings = _settings()
    assert "write_shipping" in settings.shopify_api_scopes
