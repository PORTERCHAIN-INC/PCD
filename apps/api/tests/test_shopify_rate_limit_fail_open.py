"""Shopify ingress: Redis rate-limit fail-open; HMAC still required (safe-side)."""

from __future__ import annotations

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.routers.shopify import router


def _settings() -> Settings:
    return Settings(
        shopify_api_secret="shpss_test",
        shopify_webhook_rate_limit_per_minute=300,
        shopify_carrier_rate_limit_per_minute=120,
    )


def _client(db) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = _settings
    return TestClient(app)


def test_webhook_fail_open_when_redis_down_still_requires_hmac(db) -> None:
    """Jeff-Dean safe-side: Redis outage must not skip HMAC (fail-open on limit only)."""
    client = _client(db)
    with patch(
        "porterchain_api.routers.shopify.check_fixed_window",
        return_value=(False, 0, "redis down"),
    ), patch("porterchain_api.routers.shopify.incr_rate_limit_unavailable") as bump:
        res = client.post(
            "/v1/integrations/shopify/webhooks",
            content=b'{"id":1}',
            headers={
                "X-Shopify-Shop-Domain": "acme.myshopify.com",
                "X-Shopify-Topic": "orders/create",
                "X-Shopify-Hmac-Sha256": "bad",
                "Content-Type": "application/json",
            },
        )
    assert res.status_code == 401
    bump.assert_called()


def test_carrier_fail_open_when_redis_down_still_requires_hmac(db) -> None:
    client = _client(db)
    with patch(
        "porterchain_api.routers.shopify.check_fixed_window",
        return_value=(False, 0, "redis down"),
    ):
        res = client.post(
            "/v1/integrations/shopify/carrier-service/rates",
            content=b'{"rate":{}}',
            headers={
                "X-Shopify-Shop-Domain": "acme.myshopify.com",
                "X-Shopify-Hmac-Sha256": "bad",
                "Content-Type": "application/json",
            },
        )
    assert res.status_code == 401


def test_webhook_rate_limit_exceeded_returns_429(db) -> None:
    client = _client(db)
    with patch(
        "porterchain_api.routers.shopify.check_fixed_window",
        return_value=(False, 301, None),
    ):
        res = client.post(
            "/v1/integrations/shopify/webhooks",
            content=b'{"id":1}',
            headers={
                "X-Shopify-Shop-Domain": "acme.myshopify.com",
                "X-Shopify-Topic": "orders/create",
                "X-Shopify-Hmac-Sha256": "x",
                "Content-Type": "application/json",
            },
        )
    assert res.status_code == 429
    assert res.headers.get("X-RateLimit-Limit") == "300"
