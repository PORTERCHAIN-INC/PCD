"""Prod must never fall back to localhost links in emails/SMS (Kaylulu 2026-10-15)."""

import pytest

from porterchain_api.config import (
    PUBLIC_URL_FIELDS,
    Settings,
    public_url_errors,
    require_public_urls_for_production,
)

_PROD_URLS = {
    "porterchain_api_url": "https://api.porterchain.com",
    "admin_portal_url": "https://admin.porterchain.com",
    "merchant_portal_url": "https://merchant.porterchain.com",
    "driver_portal_url": "https://driver.porterchain.com",
    "customer_portal_url": "https://customer.porterchain.com",
    "website_url": "https://porterchain.com",
    "driver_identity_return_url": "https://driver.porterchain.com/profile?identity=return",
    "stripe_connect_refresh_url": "https://merchant.porterchain.com/billing",
    "stripe_connect_return_url": "https://merchant.porterchain.com/billing?connect=return",
    "retail_checkout_success_url": "https://porterchain.com/en/book/success",
    "retail_checkout_cancel_url": "https://porterchain.com/en/book/continue",
}


def _settings(**over):
    return Settings.model_construct(**{**Settings().model_dump(), "app_env": "production", **over})


def test_local_env_allows_localhost() -> None:
    assert public_url_errors(Settings.model_construct(**{**Settings().model_dump(), "app_env": "local"})) == []


def test_production_defaults_rejected() -> None:
    s = _settings()
    errors = public_url_errors(s)
    assert any(e.startswith("WEBSITE_URL=") for e in errors)
    with pytest.raises(RuntimeError, match="WEBSITE_URL"):
        require_public_urls_for_production(s)


def test_production_real_hosts_pass() -> None:
    s = _settings(
        **_PROD_URLS,
        customer_checkout_success_url="https://customer.porterchain.com/book/success",
        customer_checkout_cancel_url="https://customer.porterchain.com/book",
    )
    assert public_url_errors(s) == []
    assert set(PUBLIC_URL_FIELDS) >= {"website_url", "merchant_portal_url"}


def test_tracking_link_uses_website_url() -> None:
    from porterchain_api.merchant_engine.tracking_views import public_track_url

    s = _settings(**_PROD_URLS)
    assert public_track_url(s, "PC-1") == "https://porterchain.com/track/PC-1"
