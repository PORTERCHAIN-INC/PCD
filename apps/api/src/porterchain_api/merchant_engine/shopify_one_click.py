"""Shopify one-click go-live + GDPR compliance handlers (ENG-G2 split)."""

from __future__ import annotations

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
        # Shopify only offers our checkout rates once it holds our CarrierService.
        "carrier_registered": any(bool(s.carrier_service_gid) for s in connected),
        # Shopify refused our token: the merchant must reopen the app to re-approve.
        "token_valid": not any(s.token_status == "token_reauth_required" for s in connected),
    }
    blocking: list[str] = []
    if not checks["oauth_configured"]:
        blocking.append("oauth_not_configured")
    if not checks["shop_connected"]:
        blocking.append("shop_not_connected")
    if checks["shop_connected"] and not checks["pickup_set"]:
        blocking.append("pickup_required")
    if checks["shop_connected"] and not checks["token_valid"]:
        blocking.append("token_reauth_required")
    if checks["shop_connected"] and not checks["carrier_registered"]:
        blocking.append("carrier_not_registered")
    if not checks["merchant_active"]:
        blocking.append("merchant_not_active")
    if not checks["has_rate_card"]:
        blocking.append("rate_card_required")
    return {
        "ready": not blocking,
        "one_click_available": checks["oauth_configured"],
        "checks": checks,
        "blocking": blocking,
        "advisories": go_live_advisories(settings, checks, connected),
    }


def go_live_advisories(settings: Settings, checks: dict[str, Any], connected: list[Any]) -> list[str]:
    """Non-blocking reminders. Never change ``ready``."""
    from porterchain_api.merchant_engine.shopify_urls import has_returns_scope

    out: list[str] = []
    # API 2026-10+: Shopify no longer auto-adds a new carrier service to the General
    # shipping profile; the merchant must switch our rates on (Markets: per market).
    if checks.get("carrier_registered") and str(settings.shopify_api_version) >= "2026-10":
        out.append("carrier_rates_enable_in_shipping")
    if (
        getattr(settings, "shopify_returns_scope_enabled", False)
        and connected
        and not any(has_returns_scope(getattr(s, "scopes", None)) for s in connected)
    ):
        out.append("returns_scope_reapprove")
    return out


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


def shop_link_status(db: Session, merchant_id: str, shop_domain: str | None) -> dict[str, Any] | None:
    """Who holds ``shop_domain``, from the signed-in company's point of view.

    ``linked_here``: this company. ``linked_elsewhere``: another company; ``can_link``
    says whether Connect may move it (dead row or unclaimed install placeholder).
    Never names the other company.
    """
    from porterchain_api.merchant_engine.shopify_service import can_rebind_shop
    from porterchain_api.merchant_engine.shopify_urls import is_shop_domain

    shop = normalize_shop_domain(shop_domain or "")
    if not shop or not is_shop_domain(shop):
        return None
    row = db.query(ShopifyShop).filter(ShopifyShop.shop_domain == shop).first()
    live = bool(row and row.uninstalled_at is None and row.encrypted_access_token)
    if row is None or not live:
        status = "not_linked" if row is None or row.merchant_id != merchant_id else "disconnected"
        return {"shop_domain": shop, "status": status, "can_link": True}
    if row.merchant_id == merchant_id:
        return {"shop_domain": shop, "status": "linked_here", "can_link": True}
    return {"shop_domain": shop, "status": "linked_elsewhere", "can_link": can_rebind_shop(db, row)}


def connection_payload(
    db: Session, merchant_id: str, settings: Settings, *, shop_domain: str | None = None
) -> dict[str, Any]:
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
        "shop_lookup": shop_link_status(db, merchant_id, shop_domain) if shop_domain else None,
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
    from porterchain_api.merchant_engine.shopify_fulfillment_service import (
        re_register_shop_hooks,
    )
    from porterchain_api.merchant_engine.shopify_service import (
        default_pickup_address,
        set_default_pickup,
    )

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
