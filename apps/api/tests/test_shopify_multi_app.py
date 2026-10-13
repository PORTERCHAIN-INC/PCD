"""Second (custom-distribution) Shopify app alongside the public one."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from types import SimpleNamespace

import jwt
import pytest

from porterchain_api.integrations.shopify_hmac import verify_webhook_hmac
from porterchain_api.merchant_engine import shopify_apps
from porterchain_api.merchant_engine.shopify_session import verify_session_token
from porterchain_api.merchant_engine.shopify_tokens import _client
from porterchain_api.merchant_engine.shopify_urls import embedded_app_url, managed_install_url

SHOP = "8hpwwc-rx.myshopify.com"
S = SimpleNamespace(
    shopify_api_key="pub",
    shopify_api_secret="pub_secret",
    shopify_extra_apps=f" cust:cust_secret:{SHOP} , broken:entry ",
)


def _tok(aud: str, secret: str, shop: str = SHOP) -> str:
    now = int(time.time())
    claims = {"aud": aud, "dest": f"https://{shop}", "iss": f"https://{shop}/admin",
              "exp": now + 60, "nbf": now - 5}
    return jwt.encode(claims, secret, algorithm="HS256")


def test_parse_skips_malformed_and_keeps_primary_first():
    assert [a.client_id for a in shopify_apps.apps(S)] == ["pub", "cust"]
    assert shopify_apps.secrets(S) == ["pub_secret", "cust_secret"]


def test_shop_pins_its_app_others_use_public():
    assert _client(S, SHOP) == {"client_id": "cust", "client_secret": "cust_secret"}
    assert _client(S, "other.myshopify.com")["client_id"] == "pub"
    assert "client_id=cust" in managed_install_url(SHOP, S)
    assert embedded_app_url(SHOP, S).endswith("/apps/cust")
    assert embedded_app_url("other.myshopify.com", S).endswith("/apps/pub")


def test_webhook_hmac_accepts_either_secret():
    body = b'{"id":1}'
    for secret in ("pub_secret", "cust_secret"):
        h = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
        assert verify_webhook_hmac(body, h, shopify_apps.secrets(S))


def test_session_token_per_app():
    assert verify_session_token(_tok("pub", "pub_secret"), S) == SHOP
    assert verify_session_token(_tok("cust", "cust_secret"), S) == SHOP
    for bad in (_tok("cust", "pub_secret"), _tok("nope", "pub_secret"),
                _tok("cust", "cust_secret", "other.myshopify.com")):
        with pytest.raises(ValueError):
            verify_session_token(bad, S)


def test_no_extras_is_unchanged():
    plain = SimpleNamespace(shopify_api_key="pub", shopify_api_secret="pub_secret")
    assert shopify_apps.secrets(plain) == ["pub_secret"]
    assert _client(plain, SHOP)["client_id"] == "pub"
