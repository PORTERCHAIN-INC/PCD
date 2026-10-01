"""Shopify one-click go-live + GDPR compliance handlers (ENG-G2 split)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.shopify_urls import (
    app_home_url,
    carrier_rates_url,
    fulfillment_callback_prefix,
    fulfillment_service_url,
    normalize_shop_domain,
    oauth_configured,
    webhook_url,
)
from porterchain_api.merchant_models import Merchant, SavedAddress, ShopifyShop


def _has_rate_card(db: Session, merchant: Merchant) -> bool:
    """True when checkout can price — merchant FSA rows or non-empty size/schedule config."""
    from porterchain_api.merchant_engine.rate_card_view import fsa_rate_counts

    cfg = merchant.pricing_config or {}
    if cfg.get("size_tiers") or cfg.get("schedule") or cfg.get("surcharges"):
        return True
    own, _shared = fsa_rate_counts(db, merchant.id)
    return own > 0


def _go_live_status(
    db: Session,
    merchant: Merchant,
    settings: Settings,
    *,
    shops: list[ShopifyShop],
) -> dict[str, Any]:
    from porterchain_api.merchant_engine.shopify_service import default_pickup_address

    connected = [
        s
        for s in shops
        if s.uninstalled_at is None and bool(s.encrypted_access_token)
    ]
    pickup_ok = False
    for shop in connected:
        if default_pickup_address(db, merchant.id, shop=shop):
            pickup_ok = True
            break
    if not pickup_ok and not connected:
        # Pre-connect: merchant already has a warehouse to bind on one-click install.
        pickup_ok = default_pickup_address(db, merchant.id) is not None

    checks = {
        "oauth_configured": oauth_configured(settings),
        "shop_connected": bool(connected),
        "pickup_set": pickup_ok and bool(connected),
        "merchant_active": merchant.status == MerchantStatus.ACTIVE.value,
        "has_rate_card": _has_rate_card(db, merchant),
    }
    blocking: list[str] = []
    if not checks["oauth_configured"]:
        blocking.append("oauth_not_configured")
    if not checks["shop_connected"]:
        blocking.append("shop_not_connected")
    if checks["shop_connected"] and not checks["pickup_set"]:
        blocking.append("pickup_required")
    if not checks["merchant_active"]:
        blocking.append("merchant_not_active")
    if not checks["has_rate_card"]:
        blocking.append("rate_card_required")
    return {
        "ready": not blocking,
        "one_click_available": checks["oauth_configured"],
        "checks": checks,
        "blocking": blocking,
    }


def ensure_shop_pickup_bound(
    db: Session,
    shop: ShopifyShop,
    *,
    address: SavedAddress | None = None,
) -> ShopifyShop:
    """Fill a null shop pickup from the merchant warehouse. No-op when already set."""
    from porterchain_api.merchant_engine.shopify_service import default_pickup_address

    if getattr(shop, "uninstalled_at", None) is not None or getattr(
        shop, "default_pickup_address_id", None
    ):
        return shop
    addr = address if isinstance(address, SavedAddress) else None
    if addr is None or addr.merchant_id != shop.merchant_id:
        resolved = default_pickup_address(db, shop.merchant_id, shop=shop)
        addr = resolved if isinstance(resolved, SavedAddress) else None
    if addr is None or not isinstance(addr.id, str):
        return shop
    shop.default_pickup_address_id = addr.id
    db.commit()
    db.refresh(shop)
    return shop


def bind_merchant_shop_pickups(db: Session, merchant_id: str) -> None:
    """Link every installed shop that has no pickup yet."""
    shops = (
        db.query(ShopifyShop)
        .filter(
            ShopifyShop.merchant_id == merchant_id,
            ShopifyShop.uninstalled_at.is_(None),
            ShopifyShop.default_pickup_address_id.is_(None),
        )
        .all()
    )
    for shop in shops:
        ensure_shop_pickup_bound(db, shop)


def connection_payload(db: Session, merchant_id: str, settings: Settings) -> dict[str, Any]:
    from porterchain_api.merchant_engine.shopify_service import default_pickup_address

    merchant = db.get(Merchant, merchant_id)
    shops = (
        db.query(ShopifyShop)
        .filter(ShopifyShop.merchant_id == merchant_id)
        .order_by(ShopifyShop.created_at.desc())
        .all()
    )
    rows = []
    for shop in shops:
        pickup = default_pickup_address(db, merchant_id, shop=shop)
        rows.append(
            {
                "id": shop.id,
                "shop_domain": shop.shop_domain,
                "connected": shop.uninstalled_at is None and bool(shop.encrypted_access_token),
                "installed_at": shop.installed_at.isoformat() if shop.installed_at else None,
                "uninstalled_at": shop.uninstalled_at.isoformat() if shop.uninstalled_at else None,
                "default_pickup_address_id": shop.default_pickup_address_id,
                "default_pickup": pickup.formatted if pickup else None,
                "has_webhook_secret": bool(shop.encrypted_webhook_secret),
                "carrier_registered": bool(shop.carrier_service_gid),
                "fulfillment_service_registered": bool(shop.fulfillment_service_gid),
            }
        )
    go_live = (
        _go_live_status(db, merchant, settings, shops=shops)
        if merchant
        else {
            "ready": False,
            "one_click_available": oauth_configured(settings),
            "checks": {},
            "blocking": ["merchant_not_found"],
        }
    )
    return {
        "oauth_configured": oauth_configured(settings),
        "webhook_url": webhook_url(settings),
        "carrier_rates_url": carrier_rates_url(settings),
        "fulfillment_service_url": fulfillment_service_url(settings),
        "fulfillment_callback_url": fulfillment_callback_prefix(settings),
        "fulfillment_service_enabled": bool(settings.shopify_fulfillment_service_enabled),
        "service_area": (
            "Canadian addresses are accepted. Checkout rates are returned only when both "
            "ends are inside the priced tile (GTA ±150 km)."
        ),
        "buyer_data_purpose": (
            "Buyer name, phone, and email are stored for delivery and privacy requests only. "
            "They are not used for marketing."
        ),
        "app_url": app_home_url(settings),
        "shops": rows,
        "go_live": go_live,
    }


def go_live(
    db: Session,
    ctx: MerchantContext,
    settings: Settings,
    *,
    shop_id: str | None = None,
    pickup_address_id: str | None = None,
) -> dict[str, Any]:
    """One action after OAuth: bind pickup (if needed) and re-register Shopify hooks."""
    from porterchain_api.merchant_engine.shopify_fulfillment_service import re_register_shop_hooks
    from porterchain_api.merchant_engine.shopify_service import default_pickup_address, set_default_pickup

    q = db.query(ShopifyShop).filter(ShopifyShop.merchant_id == ctx.merchant.id)
    if shop_id:
        shop = q.filter(ShopifyShop.id == shop_id).first()
    else:
        shop = (
            q.filter(
                ShopifyShop.uninstalled_at.is_(None),
                ShopifyShop.encrypted_access_token.isnot(None),
            )
            .order_by(ShopifyShop.created_at.desc())
            .first()
        )
    if not shop:
        raise LookupError("shop_not_found")

    addr_id = pickup_address_id or shop.default_pickup_address_id
    if not addr_id:
        fallback = default_pickup_address(db, ctx.merchant.id)
        addr_id = fallback.id if fallback else None
    if addr_id:
        set_default_pickup(db, ctx, shop.id, addr_id)
        db.refresh(shop)

    hooks = re_register_shop_hooks(shop, settings)
    payload = connection_payload(db, ctx.merchant.id, settings)
    payload["hooks"] = hooks
    return payload



def handle_gdpr_topic(
    db: Session,
    settings: Settings,
    *,
    topic: str,
    shop: ShopifyShop | None,
    raw_body: bytes,
    webhook_id: str | None = None,
) -> dict[str, Any]:
    """Open a privacy case. The reply has no buyer fields; the worker does the wipe."""
    del settings
    from porterchain_api.merchant_engine.shopify_privacy import open_privacy_request

    opened = open_privacy_request(
        db, topic=topic, shop=shop, raw_body=raw_body, webhook_id=webhook_id
    )
    if opened.get("duplicate"):
        return {"ok": True, "duplicate": True}
    return {"ok": True, "request_id": opened.get("request_id")}

