"""Rejected embedded session tokens log a reason (no token contents beyond aud/shop)."""

from __future__ import annotations

import logging
import time
from types import SimpleNamespace

import jwt
import pytest

from porterchain_api.merchant_engine.shopify_session import verify_session_token

S = SimpleNamespace(shopify_api_key="pub", shopify_api_secret="pub_secret_" + "x" * 32,
                    shopify_extra_apps="cust:cust_secret_" + "y" * 32 + ":8hpwwc-rx.myshopify.com")


def _tok(aud, secret, shop):
    now = int(time.time())
    return jwt.encode({"aud": aud, "dest": f"https://{shop}", "iss": f"https://{shop}/admin",
                       "exp": now + 60, "nbf": now - 5}, secret, algorithm="HS256")


def test_custom_app_on_other_shop_logs_reason(caplog):
    caplog.set_level(logging.WARNING)
    with pytest.raises(ValueError, match="session_token_invalid"):
        verify_session_token(_tok("cust", "cust_secret_" + "y" * 32, "pcdc-cx4c0tpx.myshopify.com"), S)
    assert "reason=custom_app_wrong_shop" in caplog.text and "pinned=8hpwwc-rx" in caplog.text


def test_bad_signature_logs_reason(caplog):
    caplog.set_level(logging.WARNING)
    with pytest.raises(ValueError):
        verify_session_token(_tok("pub", "wrong" * 8, "pcdc-cx4c0tpx.myshopify.com"), S)
    assert "reason=InvalidSignatureError aud=pub" in caplog.text


def test_public_app_ok():
    assert verify_session_token(_tok("pub", S.shopify_api_secret, "pcdc-cx4c0tpx.myshopify.com"), S) == "pcdc-cx4c0tpx.myshopify.com"
