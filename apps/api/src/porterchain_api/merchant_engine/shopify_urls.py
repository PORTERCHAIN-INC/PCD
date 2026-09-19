"""Shopify URL / OAuth state helpers — extracted from shopify_service (ENG-G2)."""

from __future__ import annotations

import json
import secrets
import time
from urllib.parse import urlencode

from porterchain_api.config import Settings
from porterchain_api.merchant_engine.secrets import decrypt_signing_secret, encrypt_signing_secret

_SHOP_RE = r"^[a-z0-9][a-z0-9\-]*\.myshopify\.com$"
_STATE_TTL_S = 600


def normalize_shop_domain(value: str) -> str:
    raw = (value or "").strip().lower()
    raw = raw.removeprefix("https://").removeprefix("http://").split("/", 1)[0]
    if raw and "." not in raw:
        raw = f"{raw}.myshopify.com"
    return raw


def is_shop_domain(value: str) -> bool:
    import re

    return bool(re.fullmatch(_SHOP_RE, value))


def sign_oauth_state(merchant_id: str | None, settings: Settings) -> str:
    payload = json.dumps(
        {"m": merchant_id or "", "n": secrets.token_hex(8), "t": int(time.time())},
        separators=(",", ":"),
    )
    return encrypt_signing_secret(payload, encryption_key=settings.jwt_secret)


def read_oauth_state(state: str | None, settings: Settings) -> str | None:
    if not state:
        return None
    try:
        raw = decrypt_signing_secret(state, encryption_key=settings.jwt_secret)
        data = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        raise ValueError("oauth_state_invalid") from None
    ts = int(data.get("t") or 0)
    if abs(time.time() - ts) > _STATE_TTL_S:
        raise ValueError("oauth_state_expired")
    merchant_id = str(data.get("m") or "").strip()
    return merchant_id or None


def webhook_url(settings: Settings) -> str:
    return f"{settings.porterchain_api_url.rstrip('/')}/v1/integrations/shopify/webhooks"


def carrier_rates_url(settings: Settings) -> str:
    return (
        f"{settings.porterchain_api_url.rstrip('/')}/v1/integrations/shopify/carrier-service/rates"
    )


def app_home_url(settings: Settings, *, shop_domain: str | None = None) -> str:
    base = f"{settings.merchant_portal_url.rstrip('/')}/shopify"
    if shop_domain:
        return f"{base}?shop={normalize_shop_domain(shop_domain)}&connected=1"
    return base


def callback_url(settings: Settings) -> str:
    return f"{settings.porterchain_api_url.rstrip('/')}/v1/integrations/shopify/callback"


def oauth_configured(settings: Settings) -> bool:
    return bool(settings.shopify_api_key and settings.shopify_api_secret)


def install_url(shop_domain: str, settings: Settings, *, merchant_id: str | None) -> str:
    if not oauth_configured(settings):
        raise ValueError("shopify_oauth_not_configured")
    shop = normalize_shop_domain(shop_domain)
    if not is_shop_domain(shop):
        raise ValueError("shop_domain_invalid")
    params = {
        "client_id": settings.shopify_api_key,
        "scope": settings.shopify_api_scopes,
        "redirect_uri": callback_url(settings),
        "state": sign_oauth_state(merchant_id, settings),
    }
    return f"https://{shop}/admin/oauth/authorize?{urlencode(params)}"
