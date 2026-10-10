"""Shopify URL / OAuth state helpers — extracted from shopify_service (ENG-G2)."""

from __future__ import annotations

import base64
import json
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlencode

from porterchain_api.config import Settings
from porterchain_api.merchant_engine.secrets import decrypt_signing_secret, encrypt_signing_secret

_SHOP_RE = r"^[a-z0-9][a-z0-9\-]*\.myshopify\.com$"
_STATE_TTL_S = 600


@dataclass(frozen=True, slots=True)
class OAuthState:
    """Signed install state: merchant seat + optional one-click pickup bind."""

    merchant_id: str | None
    pickup_address_id: str | None = None


def normalize_shop_domain(value: str) -> str:
    raw = (value or "").strip().lower()
    raw = raw.removeprefix("https://").removeprefix("http://").split("/", 1)[0]
    if raw and "." not in raw:
        raw = f"{raw}.myshopify.com"
    return raw


def is_shop_domain(value: str) -> bool:
    import re

    return bool(re.fullmatch(_SHOP_RE, value))


def sign_oauth_state(
    merchant_id: str | None,
    settings: Settings,
    *,
    pickup_address_id: str | None = None,
) -> str:
    payload = json.dumps(
        {
            "m": merchant_id or "",
            "p": (pickup_address_id or "").strip(),
            "n": secrets.token_hex(8),
            "t": int(time.time()),
        },
        separators=(",", ":"),
    )
    return encrypt_signing_secret(payload, encryption_key=settings.jwt_secret)


def read_oauth_state(state: str | None, settings: Settings) -> OAuthState:
    if not state:
        return OAuthState(merchant_id=None)
    try:
        raw = decrypt_signing_secret(state, encryption_key=settings.jwt_secret)
        data = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        raise ValueError("oauth_state_invalid") from None
    ts = int(data.get("t") or 0)
    if abs(time.time() - ts) > _STATE_TTL_S:
        raise ValueError("oauth_state_expired")
    merchant_id = str(data.get("m") or "").strip() or None
    pickup = str(data.get("p") or "").strip() or None
    return OAuthState(merchant_id=merchant_id, pickup_address_id=pickup)


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


def shopify_admin_app_url(
    settings: Settings,
    shop_domain: str,
    host: str | None = None,
) -> str:
    """App homepage inside Shopify admin, after the merchant grants access."""
    api_key = settings.shopify_api_key
    raw_host = (host or "").strip()
    if raw_host:
        padded = raw_host + ("=" * ((4 - len(raw_host) % 4) % 4))
        try:
            decoded = base64.urlsafe_b64decode(padded).decode()
        except (ValueError, UnicodeDecodeError):
            decoded = ""
        if decoded.startswith("admin.shopify.com/store/") or decoded.endswith(".myshopify.com/admin"):
            return f"https://{decoded.rstrip('/')}/apps/{api_key}"
    handle = normalize_shop_domain(shop_domain).removesuffix(".myshopify.com")
    return f"https://admin.shopify.com/store/{handle}/apps/{api_key}"


def app_home_url(
    settings: Settings,
    *,
    shop_domain: str | None = None,
    host: str | None = None,
    rates: str | None = None,
) -> str:
    """Configured app homepage. This is where a finished install must land.

    ``rates`` is ``ready`` only when Shopify holds our CarrierService; otherwise it
    names what is missing so the page never claims checkout rates it cannot serve.
    """
    base = f"{settings.merchant_portal_url.rstrip('/')}/shopify"
    if not shop_domain:
        return base
    params = {"shop": normalize_shop_domain(shop_domain), "connected": "1"}
    if rates:
        params["rates"] = rates
    if host:
        params["host"] = host
    return f"{base}?{urlencode(params)}"


def app_error_url(
    settings: Settings,
    *,
    code: str,
    shop_domain: str | None = None,
    host: str | None = None,
) -> str:
    """Merchant-portal page for a failed browser install step (never raw JSON)."""
    base = f"{settings.merchant_portal_url.rstrip('/')}/shopify"
    params: dict[str, str] = {}
    shop = normalize_shop_domain(shop_domain or "")
    if shop and is_shop_domain(shop):
        params["shop"] = shop
    import re

    params["error"] = re.sub(r"[^a-z0-9_]", "", (code or "").lower())[:64] or "install_failed"
    if host:
        params["host"] = host
    return f"{base}?{urlencode(params)}"


def callback_url(settings: Settings) -> str:
    return f"{settings.porterchain_api_url.rstrip('/')}/v1/integrations/shopify/callback"


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


def install_url(
    shop_domain: str,
    settings: Settings,
    *,
    merchant_id: str | None,
    pickup_address_id: str | None = None,
    grant_screen: bool = False,
) -> str:
    if not oauth_configured(settings):
        raise ValueError("shopify_oauth_not_configured")
    shop = normalize_shop_domain(shop_domain)
    if not is_shop_domain(shop):
        raise ValueError("shop_domain_invalid")
    params = {
        "client_id": settings.shopify_api_key,
        "scope": oauth_scopes(settings),
        "redirect_uri": callback_url(settings),
        "state": sign_oauth_state(
            merchant_id, settings, pickup_address_id=pickup_address_id
        ),
    }
    # Fresh install: Shopify's "authenticates after install" check expects
    # https://admin.shopify.com/store/{handle}/app/grant. After a token is
    # stored, the caller must send the merchant to the app page instead.
    if grant_screen:
        handle = shop.removesuffix(".myshopify.com")
        return f"https://admin.shopify.com/store/{handle}/app/grant?{urlencode(params)}"
    return f"https://{shop}/admin/oauth/authorize?{urlencode(params)}"
