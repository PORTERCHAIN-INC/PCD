"""Managed-install session token → stored offline token.

Kept out of shopify_service.py so that module stays inside its line cap.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.merchant_models import ShopifyShop

logger = logging.getLogger(__name__)


def ensure_carrier_rates(
    db: Session, settings: Settings, shop_domain: str, *, rehook: bool = False
) -> str:
    """Opening the app on an installed shop re-registers a missing CarrierService.

    Returns ``ready`` or the reason Shopify refused (see ``carrier_error_code``).
    Only the carrier step runs here (not the webhook sweep): the app page waits on it.
    ``rehook`` (a legacy token was just migrated) re-runs the full install hooks once,
    because webhooks and the carrier were refused while the old token was in use.
    """
    from porterchain_api.merchant_engine.shopify_fulfillment_ops import (
        _register_carrier_service,
        carrier_error_code,
    )
    from porterchain_api.merchant_engine.shopify_urls import normalize_shop_domain

    shop = normalize_shop_domain(shop_domain)
    row = (
        db.query(ShopifyShop)
        .filter(ShopifyShop.shop_domain == shop, ShopifyShop.uninstalled_at.is_(None))
        .first()
    )
    if row is None or not getattr(row, "encrypted_access_token", None):
        return "carrier_no_token"
    if rehook:
        from porterchain_api.merchant_engine import shopify_service as shopify

        shopify._post_install_hooks(row, settings)  # sets row.install_hooks
        return rates_status(row)
    if getattr(row, "carrier_service_gid", None):
        return "ready"
    try:
        _register_carrier_service(row, settings)
    except Exception as exc:  # noqa: BLE001 — the page shows the reason instead
        logger.warning("shopify_carrier_heal_failed shop=%s", shop, exc_info=True)
        return carrier_error_code(exc)
    return "ready"


def is_unclaimed_install_merchant(db: Session, merchant_id: str, shop_domain: str) -> bool:
    """True for the placeholder company a Shopify install made that no one has signed in to.

    ``_merchant_for_install`` creates it (profile.source = Shopify install, this shop)
    with only ``pending:``/``shopify:`` seats. A real Clerk seat means a person owns it.
    """
    from porterchain_api.merchant_engine.activation_service import SIGNUP_SOURCE_SHOPIFY
    from porterchain_api.merchant_engine.shopify_urls import normalize_shop_domain
    from porterchain_api.merchant_models import Merchant, MerchantUser

    owner = db.get(Merchant, merchant_id)
    if owner is None:
        return True
    profile = owner.profile if isinstance(owner.profile, dict) else {}
    if profile.get("source") != SIGNUP_SOURCE_SHOPIFY:
        return False
    if normalize_shop_domain(str(profile.get("shopify_shop_domain") or "")) != shop_domain:
        return False
    claimed = (
        db.query(MerchantUser.id)
        .filter(
            MerchantUser.merchant_id == owner.id,
            MerchantUser.is_active.is_(True),
            MerchantUser.clerk_user_id.isnot(None),
            ~MerchantUser.clerk_user_id.startswith("pending:"),
            ~MerchantUser.clerk_user_id.startswith("shopify:"),
        )
        .first()
    )
    return claimed is None


def can_rebind_shop(db: Session, row: ShopifyShop) -> bool:
    """A store row may move to another company only when nobody is really using it."""
    if row.uninstalled_at is not None or not row.encrypted_access_token:
        return True
    return is_unclaimed_install_merchant(db, row.merchant_id, row.shop_domain)


def rates_status(shop: ShopifyShop | None) -> str:
    """``ready`` when Shopify has our CarrierService, else the reason it does not."""
    if shop is None:
        return "carrier_register_failed"
    if getattr(shop, "carrier_service_gid", None):
        return "ready"
    hooks = getattr(shop, "install_hooks", None)
    if isinstance(hooks, dict) and hooks.get("carrier_error"):
        return str(hooks["carrier_error"])
    return "carrier_register_failed"


def _exchange_session_token(shop: str, subject_token: str, settings: Settings) -> dict[str, Any]:
    """Managed-install session token → expiring offline Admin API token + refresh token."""
    from porterchain_api.merchant_engine.shopify_tokens import exchange_id_token

    return exchange_id_token(shop, subject_token, settings)


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
    from porterchain_api.merchant_engine.shopify_tokens import store_token_response

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
    store_token_response(row, token_body, settings)
    # Fallback is what we actually asked for, never the unreleased manifest list.
    from porterchain_api.merchant_engine.shopify_urls import oauth_scopes

    row.scopes = str(token_body.get("scope") or oauth_scopes(settings))
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
