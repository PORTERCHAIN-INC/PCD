"""Shopify embedded app: URLs, managed install link, session token, store link."""

from __future__ import annotations

import time
import tomllib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.merchant_engine import shopify_service as shopify
from porterchain_api.merchant_engine import shopify_session as session
from porterchain_api.merchant_engine import shopify_urls as urls

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
        shopify_api_secret="shpss_test_secret_0123456789abcdef",
        fleetbase_dispatch_bridge=False,
    )


def _session_token(*, shop: str = "demo.myshopify.com", secret: str = "shpss_test_secret_0123456789abcdef", aud: str = "cid", ttl: int = 60) -> str:
    now = int(time.time())
    claims = {
        "iss": f"https://{shop}/admin",
        "dest": f"https://{shop}",
        "aud": aud,
        "sub": "42",
        "exp": now + ttl,
        "nbf": now - 5,
        "iat": now - 5,
        "jti": "jti-1",
        "sid": "sid-1",
    }
    return jwt.encode(claims, secret, algorithm="HS256")


def test_partner_app_urls() -> None:
    settings = _settings()
    assert urls.oauth_configured(settings) is True
    assert shopify.webhook_url(settings).endswith("/v1/integrations/shopify/webhooks")
    assert shopify.carrier_rates_url(settings).endswith("/v1/integrations/shopify/carrier-service/rates")
    assert shopify.fulfillment_service_url(settings).endswith(
        "/v1/integrations/shopify/fs/fulfillment_order_notification"
    )


def test_managed_install_url_has_no_oauth_state() -> None:
    url = urls.managed_install_url("Acme.myshopify.com", _settings())
    assert url == "https://admin.shopify.com/store/acme/oauth/install?client_id=cid"
    with pytest.raises(ValueError, match="shop_domain_invalid"):
        urls.managed_install_url("not a shop!", _settings())


def test_link_token_roundtrip_and_expiry() -> None:
    settings = _settings()
    token = urls.sign_link_token("Demo.myshopify.com", settings)
    assert urls.read_link_token(token, settings) == "demo.myshopify.com"
    with pytest.raises(ValueError, match="link_token_invalid"):
        urls.read_link_token("garbage", settings)
    with patch.object(urls.time, "time", return_value=time.time() + 3600):
        with pytest.raises(ValueError, match="link_token_expired"):
            urls.read_link_token(token, settings)


def test_session_token_verification() -> None:
    settings = _settings()
    assert session.verify_session_token(_session_token(), settings) == "demo.myshopify.com"
    for bad in (
        _session_token(secret="wrong_secret_0123456789abcdef_xyz"),
        _session_token(aud="other-app"),
        _session_token(ttl=-60),
        "not-a-jwt",
    ):
        with pytest.raises(ValueError, match="session_token_invalid"):
            session.verify_session_token(bad, settings)


def _client(db: MagicMock) -> TestClient:
    from porterchain_api.routers.shopify import router

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_settings] = _settings
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def test_session_endpoint_rejects_missing_or_forged_token() -> None:
    client = _client(MagicMock())
    assert client.post("/v1/integrations/shopify/session").status_code == 401
    forged = client.post(
        "/v1/integrations/shopify/session",
        headers={"Authorization": f"Bearer {_session_token(secret='wrong_secret_0123456789abcdef_xyz')}"},
    )
    assert forged.status_code == 401
    assert forged.json()["detail"] == "session_token_invalid"


def test_first_open_installs_then_hands_back_link_token() -> None:
    db = MagicMock()
    row = SimpleNamespace(shop_domain="demo.myshopify.com", merchant_id="m-placeholder")
    with (
        patch("porterchain_api.merchant_engine.shopify_tokens.token_state_for_open", return_value=""),
        patch.object(session, "install_from_session_token", return_value=row) as install,
        patch.object(session, "rates_status", return_value="ready"),
        patch.object(session, "_active_row", return_value=row),  # background webhook sweep + lead
        patch("porterchain_api.db.SessionLocal", return_value=MagicMock()),
        patch("porterchain_api.routers.shopify._record_install_lead") as lead,
        patch.object(session, "is_unclaimed_install_merchant", return_value=True),
    ):
        res = _client(db).post(
            "/v1/integrations/shopify/session",
            headers={"Authorization": f"Bearer {_session_token()}"},
        )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["shop_domain"] == "demo.myshopify.com"
    assert body["rates"] == "ready" and body["linked"] is False
    assert urls.read_link_token(body["link_token"], _settings()) == "demo.myshopify.com"
    install.assert_called_once()
    lead.assert_called_once()


def test_reopen_heals_rates_and_shows_linked_company() -> None:
    db = MagicMock()
    row = SimpleNamespace(shop_domain="demo.myshopify.com", merchant_id="m1")
    db.get.return_value = SimpleNamespace(company_name="Maple Leaf Supply")
    with (
        patch("porterchain_api.merchant_engine.shopify_tokens.token_state_for_open", return_value="valid"),
        patch.object(session, "ensure_carrier_rates", return_value="ready") as heal,
        patch.object(session, "_active_row", return_value=row),
        patch.object(session, "install_from_session_token") as install,
        patch.object(session, "is_unclaimed_install_merchant", return_value=False),
    ):
        body = session.open_embedded(db, _settings(), _session_token())
    assert body == {
        "shop_domain": "demo.myshopify.com",
        "rates": "ready",
        "linked": True,
        "company_name": "Maple Leaf Supply",
        "link_token": None,
    }
    heal.assert_called_once()
    install.assert_not_called()


def test_link_shop_moves_placeholder_store_to_signed_in_company() -> None:
    settings = _settings()
    db = MagicMock()
    row = SimpleNamespace(
        shop_domain="demo.myshopify.com", merchant_id="m-placeholder", default_pickup_address_id=None
    )
    token = urls.sign_link_token("demo.myshopify.com", settings)
    with (
        patch.object(session, "_active_row", return_value=row),
        patch.object(session, "can_rebind_shop", return_value=True),
        patch.object(shopify, "default_pickup_address", return_value=SimpleNamespace(id="addr-1")),
    ):
        out = session.link_shop(db, "m-real", settings, token)
    assert out.merchant_id == "m-real"
    assert out.default_pickup_address_id == "addr-1"
    db.commit.assert_called_once()


def test_link_shop_refuses_a_store_another_company_uses() -> None:
    settings = _settings()
    row = SimpleNamespace(shop_domain="demo.myshopify.com", merchant_id="m-other")
    token = urls.sign_link_token("demo.myshopify.com", settings)
    with (
        patch.object(session, "_active_row", return_value=row),
        patch.object(session, "can_rebind_shop", return_value=False),
    ):
        with pytest.raises(ValueError, match="shop_already_connected"):
            session.link_shop(MagicMock(), "m-real", settings, token)
    assert row.merchant_id == "m-other"


def test_app_toml_is_embedded_managed_install() -> None:
    """Partners manifest tracks API defaults; client_id stays empty in git."""
    settings = _settings()
    raw = tomllib.loads(_APP_TOML.read_text(encoding="utf-8"))

    assert raw.get("client_id") == ""
    assert raw["embedded"] is True
    assert raw["application_url"] == f"{settings.merchant_portal_url}/shopify-app"
    # Released scopes only (returns are off): the grant screen asks for nothing unused.
    from porterchain_api.merchant_engine.shopify_urls import oauth_scopes

    assert set(raw["access_scopes"]["scopes"].split(",")) == set(oauth_scopes(settings).split(","))
    assert raw["access_scopes"]["use_legacy_install_flow"] is False
    assert "auth" not in raw  # no OAuth redirect: Shopify manages install
    assert raw["webhooks"]["api_version"] == settings.shopify_api_version == "2026-10"

    topics: set[str] = set()
    compliance: set[str] = set()
    for sub in raw["webhooks"]["subscriptions"]:
        assert sub["uri"] == shopify.webhook_url(settings)
        topics.update(sub.get("topics") or [])
        compliance.update(sub.get("compliance_topics") or [])
    assert {"orders/create", "orders/cancelled", "app/uninstalled"} <= topics
    assert {"customers/data_request", "customers/redact", "shop/redact"} <= compliance
    assert "fulfillment_orders/fulfillment_request_submitted" not in topics
