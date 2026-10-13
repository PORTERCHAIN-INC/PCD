"""Shopify app credentials: the public app + optional custom-distribution apps.

``SHOPIFY_EXTRA_APPS`` = comma list of ``client_id:secret:shop.myshopify.com``.
A custom-distribution app installs on exactly one store, so the shop pins the app:
token exchange/refresh and install links for that shop use its pair; HMAC and
session tokens are accepted from any configured app.
"""

from __future__ import annotations

from typing import Any, NamedTuple


class ShopifyApp(NamedTuple):
    client_id: str
    secret: str
    shop: str = ""


def _norm(shop: str) -> str:
    return shop.strip().lower().removeprefix("https://").removeprefix("http://").rstrip("/")


def apps(settings: Any) -> list[ShopifyApp]:
    """Primary first, then extras. Malformed extras are skipped."""
    out: list[ShopifyApp] = []
    key = getattr(settings, "shopify_api_key", "") or ""
    secret = getattr(settings, "shopify_api_secret", "") or ""
    if key or secret:
        out.append(ShopifyApp(key, secret))
    for entry in str(getattr(settings, "shopify_extra_apps", "") or "").split(","):
        parts = [p.strip() for p in entry.split(":")]
        if len(parts) == 3 and all(parts):
            out.append(ShopifyApp(parts[0], parts[1], _norm(parts[2])))
    return out


def secrets(settings: Any) -> list[str]:
    return [a.secret for a in apps(settings) if a.secret]


def by_client_id(settings: Any, client_id: str | None) -> ShopifyApp | None:
    return next((a for a in apps(settings) if client_id and a.client_id == client_id), None)


def for_shop(settings: Any, shop: str | None) -> ShopifyApp:
    """The app pinned to this shop, else the primary app."""
    shop = _norm(shop or "")
    pinned = next((a for a in apps(settings) if a.shop and a.shop == shop), None)
    return pinned or ShopifyApp(
        getattr(settings, "shopify_api_key", "") or "",
        getattr(settings, "shopify_api_secret", "") or "",
    )
