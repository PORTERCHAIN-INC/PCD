"""Shopify one-click go-live + GDPR compliance handlers (ENG-G2 split)."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.shopify_urls import (
    app_home_url,
    carrier_rates_url,
    fulfillment_service_url,
    normalize_shop_domain,
    oauth_configured,
    webhook_url,
)
from porterchain_api.merchant_models import Merchant, ShopifyShop
from porterchain_api.booking_models import Order

logger = logging.getLogger("porterchain.shopify_one_click")


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
        "fulfillment_service_enabled": bool(settings.shopify_fulfillment_service_enabled),
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
) -> dict[str, Any]:
    """Mandatory Partners compliance webhooks — redact / acknowledge without dumping PII."""
    try:
        payload = json.loads(raw_body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    shop_domain = normalize_shop_domain(
        str(payload.get("shop_domain") or (shop.shop_domain if shop else "") or "")
    )
    logger.info(
        "shopify_gdpr topic=%s shop=%s keys=%s",
        topic,
        shop_domain or "unknown",
        sorted(str(k) for k in payload.keys())[:12],
    )

    if topic == "shop/redact":
        target = shop
        if target is None and shop_domain:
            target = (
                db.query(ShopifyShop).filter(ShopifyShop.shop_domain == shop_domain).first()
            )
        if target:
            target.uninstalled_at = datetime.now(UTC)
            target.encrypted_access_token = None
            target.encrypted_webhook_secret = None
            target.default_pickup_address_id = None
            db.commit()
        return {"ok": True, "redacted": "shop"}

    if topic == "customers/redact":
        customer = payload.get("customer") if isinstance(payload.get("customer"), dict) else {}
        email = str(customer.get("email") or "").strip().lower()
        phone = str(customer.get("phone") or "").strip()
        if shop and (email or phone):
            orders = (
                db.query(Order)
                .filter(Order.merchant_id == shop.merchant_id)
                .order_by(Order.created_at.desc())
                .limit(200)
                .all()
            )
            touched = 0
            for order in orders:
                meta = dict(order.compliance_metadata or {})
                shopify_meta = dict(meta.get("shopify") or {})
                cust = shopify_meta.get("customer") if isinstance(shopify_meta.get("customer"), dict) else {}
                match = False
                if email and str(cust.get("email") or "").strip().lower() == email:
                    match = True
                if phone and str(cust.get("phone") or "").strip() == phone:
                    match = True
                if not match:
                    continue
                shopify_meta["customer"] = {
                    "id": cust.get("id"),
                    "email": None,
                    "phone": None,
                    "redacted_at": datetime.now(UTC).isoformat(),
                }
                meta["shopify"] = shopify_meta
                order.compliance_metadata = meta
                db.add(order)
                touched += 1
            if touched:
                db.commit()
            return {"ok": True, "redacted": "customers", "orders": touched}
        return {"ok": True, "redacted": "customers", "orders": 0}

    # customers/data_request — ack immediately; ops can fulfill export offline.
    return {"ok": True, "received": "customers/data_request"}

