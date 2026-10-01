"""Managed-install session token → stored offline token.

Kept out of shopify_service.py so that module stays inside its line cap.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.merchant_models import ShopifyShop


def shop_has_offline_token(db: Session, shop_domain: str) -> bool:
    """True when this shop already completed install and we stored a token."""
    from porterchain_api.merchant_engine.shopify_urls import is_shop_domain, normalize_shop_domain

    shop = normalize_shop_domain(shop_domain)
    if not is_shop_domain(shop):
        return False
    row = (
        db.query(ShopifyShop)
        .filter(ShopifyShop.shop_domain == shop, ShopifyShop.uninstalled_at.is_(None))
        .first()
    )
    return bool(row and row.encrypted_access_token)


def _exchange_session_token(shop: str, subject_token: str, settings: Settings) -> dict[str, Any]:
    """Managed-install session token → offline Admin API token."""
    url = f"https://{shop}/admin/oauth/access_token"
    with httpx.Client(timeout=15.0) as client:
        response = client.post(
            url,
            data={
                "client_id": settings.shopify_api_key,
                "client_secret": settings.shopify_api_secret,
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "subject_token": subject_token,
                "subject_token_type": "urn:ietf:params:oauth:token-type:id_token",
                "requested_token_type": "urn:shopify:params:oauth:token-type:offline-access-token",
            },
        )
        response.raise_for_status()
        body = response.json()
    return body if isinstance(body, dict) else {}


def install_from_session_token(
    db: Session,
    settings: Settings,
    *,
    shop_domain: str,
    id_token: str,
) -> ShopifyShop:
    """Store an offline token from Shopify's post-auth id_token."""
    from porterchain_api.merchant_engine import shopify_service as shopify
    from porterchain_api.merchant_engine.activation_service import (
        SIGNUP_SOURCE_SHOPIFY,
        apply_signup_policy,
    )

    if not shopify.oauth_configured(settings):
        raise ValueError("shopify_oauth_not_configured")
    shop = shopify.normalize_shop_domain(shop_domain)
    if not shopify.is_shop_domain(shop):
        raise ValueError("shop_domain_invalid")
    token_body = _exchange_session_token(shop, id_token, settings)
    access_token = str(token_body.get("access_token") or "")
    if not access_token:
        raise ValueError("oauth_token_missing")
    shop_info = shopify._admin_get(shop, access_token, "/shop.json", settings) or {}
    shop_payload = shop_info.get("shop") if isinstance(shop_info.get("shop"), dict) else {}
    if not isinstance(shop_payload, dict):
        shop_payload = {}
    merchant = shopify._merchant_for_install(db, None, shop, shop_payload)
    row = db.query(ShopifyShop).filter(ShopifyShop.shop_domain == shop).first()
    if row and row.merchant_id != merchant.id:
        raise ValueError("shop_already_connected")
    if row is None:
        row = ShopifyShop(merchant_id=merchant.id, shop_domain=shop, auto_dispatch=False)
        db.add(row)
    row.merchant_id = merchant.id
    row.encrypted_access_token = shopify._encrypt(access_token, settings)
    row.scopes = str(token_body.get("scope") or settings.shopify_api_scopes)
    gid = shop_payload.get("id")
    row.shopify_shop_gid = str(gid) if gid else row.shopify_shop_gid
    row.uninstalled_at = None
    row.installed_at = datetime.now(UTC)
    if not row.default_pickup_address_id:
        fallback = shopify.default_pickup_address(db, merchant.id)
        if fallback:
            row.default_pickup_address_id = fallback.id
    apply_signup_policy(db, merchant, source=SIGNUP_SOURCE_SHOPIFY)
    db.commit()
    db.refresh(row)
    shopify._post_install_hooks(row, settings)
    return row
