"""Embedded app: App Bridge session token → verified shop → stored offline token.

Shopify-managed install grants the scopes; the embedded page posts its session
token here, we token-exchange it once, and a portal seat claims the store with
the signed link token.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.merchant_models import ShopifyShop

logger = logging.getLogger(__name__)


def ensure_carrier_rates(db: Session, settings: Settings, shop_domain: str, *, rehook: bool = False) -> str:
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
    row = db.query(ShopifyShop).filter(ShopifyShop.shop_domain == shop, ShopifyShop.uninstalled_at.is_(None)).first()
    if row is None or not getattr(row, "encrypted_access_token", None):
        return "carrier_no_token"
    if rehook:
        from porterchain_api.merchant_engine import shopify_service as shopify

        shopify._post_install_hooks(row, settings)  # sets row.install_hooks
        return rates_status(row)
    if getattr(row, "carrier_service_gid", None) and _carrier_still_on_store(row, settings):
        return "ready"
    try:
        _register_carrier_service(row, settings)
    except Exception as exc:
        logger.warning("shopify_carrier_heal_failed shop=%s", shop, exc_info=True)
        return carrier_error_code(exc)
    return "ready"


def _carrier_still_on_store(row: ShopifyShop, settings: Settings) -> bool:
    """Stored id is trusted unless Shopify positively says the service is gone.

    A merchant (or a plan change) can delete the CarrierService; then every app open
    re-registers it. Network / auth errors keep the stored id (never block the page).
    """
    from porterchain_api.merchant_engine.shopify_admin_graphql import carrier_service_find
    from porterchain_api.merchant_engine.shopify_fulfillment_ops import access_token_for
    from porterchain_api.merchant_engine.shopify_urls import carrier_rates_url

    try:
        token = access_token_for(row, settings)
        if not token:
            return True
        found = carrier_service_find(
            row.shop_domain, token, settings, callback_url=carrier_rates_url(settings)
        )
    except Exception:  # noqa: BLE001
        return True
    if found:
        return True
    logger.warning("shopify_carrier_missing_on_store shop=%s", row.shop_domain)
    row.carrier_service_gid = None
    return False


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
    full_hooks: bool = True,
) -> ShopifyShop:
    """Store an offline token from Shopify's post-auth id_token.

    ``full_hooks=False`` registers only the CarrierService inline (the page shows its
    status); the caller runs the webhook sweep in the background.
    """
    from porterchain_api.merchant_engine import shopify_service as shopify
    from porterchain_api.merchant_engine.activation_service import (
        SIGNUP_SOURCE_SHOPIFY,
        apply_signup_policy,
    )
    from porterchain_api.merchant_engine.shopify_tokens import store_token_response
    from porterchain_api.merchant_engine.shopify_urls import oauth_configured

    if not oauth_configured(settings):
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
    merchant = shopify._merchant_for_install(db, shop, shop_payload)
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
    if full_hooks:
        shopify._post_install_hooks(row, settings)
    else:
        _register_carrier_inline(row, settings)
    return row


def _register_carrier_inline(row: ShopifyShop, settings: Settings) -> None:
    from porterchain_api.merchant_engine.shopify_fulfillment_ops import (
        _register_carrier_service,
        carrier_error_code,
    )

    try:
        _register_carrier_service(row, settings)
        row.install_hooks = {"carrier_registered": True, "carrier_error": None}
    except Exception as exc:  # noqa: BLE001
        logger.warning("shopify_carrier_register_failed shop=%s", row.shop_domain, exc_info=True)
        row.install_hooks = {"carrier_registered": False, "carrier_error": carrier_error_code(exc)}


Defer = Callable[[Callable[[], None]], None]


def _in_new_session(fn: Callable[[Session], None]) -> Callable[[], None]:
    """Background work gets its own DB session (the request's is closed by then)."""

    def run() -> None:
        from porterchain_api.db import SessionLocal

        db = SessionLocal()
        try:
            fn(db)
        except Exception:  # noqa: BLE001
            db.rollback()
            logger.exception("shopify_embedded_background_failed")
        finally:
            db.close()

    return run


def verify_session_token(token: str, settings: Settings) -> str:
    """App Bridge session token (HS256, app secret, aud = API key) → shop domain."""
    import jwt

    from porterchain_api.merchant_engine.shopify_urls import (
        is_shop_domain,
        normalize_shop_domain,
    )

    if not (settings.shopify_api_key and settings.shopify_api_secret):
        raise ValueError("shopify_oauth_not_configured")
    try:
        claims = jwt.decode(
            token,
            settings.shopify_api_secret,
            algorithms=["HS256"],
            audience=settings.shopify_api_key,
            leeway=10,
            options={"require": ["exp", "nbf", "dest", "aud"]},
        )
    except jwt.PyJWTError:
        raise ValueError("session_token_invalid") from None
    shop = normalize_shop_domain(str(claims.get("dest") or ""))
    issuer = normalize_shop_domain(str(claims.get("iss") or shop))
    if not is_shop_domain(shop) or issuer != shop:
        raise ValueError("session_token_invalid")
    return shop


def open_embedded(
    db: Session,
    settings: Settings,
    session_token: str,
    on_install: Callable[[Session, ShopifyShop], None] | None = None,
    defer: Defer | None = None,
) -> dict[str, Any]:
    """Every embedded page load: install on first open, heal rates after, report status.

    ``on_install`` runs once after a fresh install (the router records the CRM lead).
    """
    from porterchain_api.merchant_engine.shopify_tokens import token_state_for_open
    from porterchain_api.merchant_engine.shopify_urls import sign_link_token
    from porterchain_api.merchant_models import Merchant

    shop = verify_session_token(session_token, settings)
    token_state = token_state_for_open(db, settings, shop)
    if defer is None:  # inline (tests / scripts): same work, no background
        def defer(fn: Callable[[], None]) -> None:
            fn()

    if token_state:
        row = _active_row(db, shop)
        if token_state != "migrated" and getattr(row, "carrier_service_gid", None):
            # Fast path: answer from the stored id; verify it is still on the store later.
            rates = "ready"
            defer(_in_new_session(lambda bg: ensure_carrier_rates(bg, settings, shop)))
        else:
            rates = ensure_carrier_rates(db, settings, shop, rehook=token_state == "migrated")
            row = _active_row(db, shop)
    else:
        row = install_from_session_token(
            db, settings, shop_domain=shop, id_token=session_token, full_hooks=False
        )
        rates = rates_status(row)

        def _after_install(bg: Session) -> None:
            from porterchain_api.merchant_engine import shopify_service as shopify

            bg_row = _active_row(bg, shop)
            if bg_row is None:
                return
            if on_install:
                on_install(bg, bg_row)
            shopify._post_install_hooks(bg_row, settings)  # webhooks (+ carrier, idempotent)

        defer(_in_new_session(_after_install))
    merchant = db.get(Merchant, row.merchant_id) if row else None
    linked = bool(row) and not is_unclaimed_install_merchant(db, row.merchant_id, shop)
    return {
        "shop_domain": shop,
        "rates": rates,
        "linked": linked,
        "company_name": merchant.company_name if merchant and linked else None,
        "link_token": None if linked else sign_link_token(shop, settings),
    }


def link_shop(db: Session, merchant_id: str, settings: Settings, link_token: str) -> ShopifyShop:
    """A signed-in portal seat claims the store its admin installed (embedded link token)."""
    from porterchain_api.merchant_engine.shopify_service import default_pickup_address
    from porterchain_api.merchant_engine.shopify_urls import read_link_token

    shop = read_link_token(link_token, settings)
    row = _active_row(db, shop)
    if row is None:
        raise LookupError("shop_not_connected")
    if row.merchant_id != merchant_id:
        if not can_rebind_shop(db, row):
            raise ValueError("shop_already_connected")
        logger.info(
            "shopify_shop_linked shop=%s from=%s to=%s",
            shop,
            row.merchant_id,
            merchant_id,
        )
        row.merchant_id = merchant_id
        pickup = default_pickup_address(db, merchant_id)
        row.default_pickup_address_id = pickup.id if pickup else None
        db.commit()
        db.refresh(row)
    return row


def _active_row(db: Session, shop: str) -> ShopifyShop | None:
    return db.query(ShopifyShop).filter(ShopifyShop.shop_domain == shop, ShopifyShop.uninstalled_at.is_(None)).first()
