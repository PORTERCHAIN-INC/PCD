"""Shopify URLs and the signed store-link token (managed install, embedded app)."""

from __future__ import annotations

import json
import secrets
import time

from porterchain_api.config import Settings
from porterchain_api.merchant_engine.secrets import decrypt_signing_secret, encrypt_signing_secret

_SHOP_RE = r"^[a-z0-9][a-z0-9\-]*\.myshopify\.com$"
_LINK_TTL_S = 900


def normalize_shop_domain(value: str) -> str:
    raw = (value or "").strip().lower()
    raw = raw.removeprefix("https://").removeprefix("http://").split("/", 1)[0]
    if raw and "." not in raw:
        raw = f"{raw}.myshopify.com"
    return raw


def is_shop_domain(value: str) -> bool:
    import re

    return bool(re.fullmatch(_SHOP_RE, value))


def sign_link_token(shop_domain: str, settings: Settings) -> str:
    """Proof, minted inside Shopify admin, that the caller administers this store.

    The embedded app hands it to the merchant portal, where a signed-in seat
    links the store to its company (managed install carries no OAuth state).
    """
    payload = json.dumps(
        {"s": normalize_shop_domain(shop_domain), "n": secrets.token_hex(8), "t": int(time.time())},
        separators=(",", ":"),
    )
    return encrypt_signing_secret(payload, encryption_key=settings.jwt_secret)


def read_link_token(token: str | None, settings: Settings) -> str:
    """Shop domain from a link token, or ``ValueError`` (invalid / expired)."""
    try:
        data = json.loads(decrypt_signing_secret(token or "", encryption_key=settings.jwt_secret))
    except (ValueError, json.JSONDecodeError):
        raise ValueError("link_token_invalid") from None
    if abs(time.time() - int(data.get("t") or 0)) > _LINK_TTL_S:
        raise ValueError("link_token_expired")
    shop = normalize_shop_domain(str(data.get("s") or ""))
    if not is_shop_domain(shop):
        raise ValueError("link_token_invalid")
    return shop


def webhook_url(settings: Settings) -> str:
    return f"{settings.porterchain_api_url.rstrip('/')}/v1/integrations/shopify/webhooks"


def carrier_rates_url(settings: Settings) -> str:
    return (
        f"{settings.porterchain_api_url.rstrip('/')}/v1/integrations/shopify/carrier-service/rates"
    )


def fulfillment_callback_prefix(settings: Settings) -> str:
    """Shopify appends ``/fulfillment_order_notification`` to this prefix."""
    return f"{settings.porterchain_api_url.rstrip('/')}/v1/integrations/shopify/fs"


def fulfillment_service_url(settings: Settings) -> str:
    return f"{fulfillment_callback_prefix(settings)}/fulfillment_order_notification"


def oauth_configured(settings: Settings) -> bool:
    return bool(settings.shopify_api_key and settings.shopify_api_secret)


# Scopes released on PorterChain Delivery. Extra env scopes (read_products,
# write_orders, …) make Shopify's grant screen refuse the automated install.
_RELEASED_APP_SCOPES = (
    "read_assigned_fulfillment_orders",
    "read_merchant_managed_fulfillment_orders",
    "read_orders",
    "write_assigned_fulfillment_orders",
    "write_fulfillments",
    "write_merchant_managed_fulfillment_orders",
    "write_shipping",
)


#: Released only once the app version carrying it is live (settings flag).
RETURNS_SCOPE = "read_returns"


def oauth_scopes(settings: Settings) -> str:
    requested = [part.strip() for part in settings.shopify_api_scopes.split(",") if part.strip()]
    allowed = [part for part in requested if part in _RELEASED_APP_SCOPES]
    scopes = allowed or list(_RELEASED_APP_SCOPES)
    if getattr(settings, "shopify_returns_scope_enabled", False) and RETURNS_SCOPE not in scopes:
        scopes = [*scopes, RETURNS_SCOPE]
    return ",".join(scopes)


def has_returns_scope(granted: str | None) -> bool:
    # write_returns includes read_returns (Shopify omits the implied read scope).
    parts = {part.strip() for part in str(granted or "").split(",")}
    return RETURNS_SCOPE in parts or "write_returns" in parts


def managed_install_url(shop_domain: str, settings: Settings) -> str:
    """Shopify-managed install: Shopify grants the toml scopes, then opens the embedded app."""
    if not oauth_configured(settings):
        raise ValueError("shopify_oauth_not_configured")
    shop = normalize_shop_domain(shop_domain)
    if not is_shop_domain(shop):
        raise ValueError("shop_domain_invalid")
    handle = shop.removesuffix(".myshopify.com")
    return f"https://admin.shopify.com/store/{handle}/oauth/install?client_id={settings.shopify_api_key}"
