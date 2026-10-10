"""One status for a Shopify store, shared by the merchant portal, admin and super admin.

Before this, three views computed "connected / paused / healthy" three ways
(token vs no token, DLQ open vs open+held, paused amber vs not shown at all),
so the same store could look live to the merchant and broken to staff.

Every view now calls :func:`shop_health` and renders ``light`` + ``reason`` +
``fix``. ``problems`` keeps every issue in order of severity (first one wins).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.merchant_models import ShopifyIngressDlq, ShopifyShop

STALE_ORDERS_DAYS = 7
DLQ_WAITING = ("open", "held")

# code -> (plain sentence, fix code). Fix codes are the same in every UI.
_COPY: dict[str, tuple[str, str | None]] = {
    "uninstalled": ("Store disconnected — orders are not coming in", "reconnect"),
    "token_reauth": ("Shopify access expired — reopen the app in Shopify to approve again", "reconnect"),
    "no_token": ("Store not authorised yet", "reconnect"),
    "scopes_missing": ("Missing Shopify permissions", "reconnect"),
    "paused": ("New orders paused by PorterChain staff", "resume_orders"),
    "orders_waiting": ("{n} order{s} couldn't be booked", "review_failed_orders"),
    "pickup_missing": ("No pickup address — orders can't be booked", "add_pickup"),
    "carrier_missing": ("Checkout shipping rates not set up", "repair_setup"),
    "tracking_failing": ("Tracking isn't reaching Shopify for recent orders", "retry_tracking"),
}


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def scope_set(raw: str | None) -> set[str]:
    have = {p.strip() for p in str(raw or "").split(",") if p.strip()}
    # Shopify reports write_X without read_X; a write grant includes read.
    return have | {"read_" + s[len("write_"):] for s in have if s.startswith("write_")}


def missing_scopes(granted: str | None, required: str) -> list[str]:
    wanted = {p.strip() for p in str(required or "").split(",") if p.strip()}
    return sorted(wanted - scope_set(granted))


def is_connected(shop: ShopifyShop) -> bool:
    """Same rule everywhere: installed and holding a token."""
    return shop.uninstalled_at is None and bool(shop.encrypted_access_token)


def waiting_orders(db: Session, shop: ShopifyShop) -> int:
    """Orders that reached us but did not become bookings (failed or held while paused)."""
    return (
        db.query(ShopifyIngressDlq)
        .filter(ShopifyIngressDlq.shop_id == shop.id, ShopifyIngressDlq.status.in_(DLQ_WAITING))
        .count()
    )


def tracking_failures(db: Session, shop: ShopifyShop, *, recent: int = 20) -> list[str]:
    """Recent orders whose fulfillment/tracking push to Shopify failed (order ids)."""
    from porterchain_api.booking_models import Order
    from porterchain_api.domain.states import OrderSource

    rows = (
        db.query(Order)
        .filter(Order.merchant_id == shop.merchant_id, Order.order_source == OrderSource.SHOPIFY.value)
        .order_by(Order.created_at.desc())
        .limit(recent)
        .all()
    )
    out = []
    for order in rows:
        meta = (order.compliance_metadata or {}).get("shopify") or {}
        if meta.get("shop_domain") == shop.shop_domain and meta.get("last_fulfillment_error"):
            out.append(order.id)
    return out


def shop_health(
    db: Session,
    shop: ShopifyShop,
    settings: Any,
    *,
    pickup_set: bool | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    from porterchain_api.merchant_engine.shopify_urls import oauth_scopes

    now = now or datetime.now(UTC)
    if pickup_set is None:
        from porterchain_api.merchant_engine.shopify_service import (
            default_pickup_address,
        )

        pickup_set = default_pickup_address(db, shop.merchant_id, shop=shop) is not None
    connected = is_connected(shop)
    missing = missing_scopes(shop.scopes, oauth_scopes(settings)) if connected else []
    waiting = waiting_orders(db, shop)

    codes: list[str] = []
    if shop.uninstalled_at is not None:
        codes.append("uninstalled")
    elif getattr(shop, "token_status", None) == "token_reauth_required":
        codes.append("token_reauth")
    elif not shop.encrypted_access_token:
        codes.append("no_token")
    if connected:
        if missing:
            codes.append("scopes_missing")
        if shop.ingress_paused:
            codes.append("paused")
    if waiting:
        codes.append("orders_waiting")
    if connected:
        if not pickup_set:
            codes.append("pickup_missing")
        if not shop.carrier_service_gid:
            codes.append("carrier_missing")
    failing = tracking_failures(db, shop) if connected else []
    if failing:
        codes.append("tracking_failing")

    def text(code: str) -> str:
        return _COPY[code][0].format(n=waiting, s="" if waiting == 1 else "s")

    last = _aware(shop.last_webhook_at)
    if codes:
        light, reason, fix = "red", text(codes[0]), _COPY[codes[0]][1]
    elif last is None or now - last > timedelta(days=STALE_ORDERS_DAYS):
        light, reason, fix = "amber", "Connected, no recent orders", "backfill"
    else:
        light, reason, fix = "green", "Connected and receiving orders", None
    return {
        "state": (
            "disconnected" if not connected else "paused" if shop.ingress_paused else "connected"
        ),
        "connected": connected,
        "paused": bool(connected and shop.ingress_paused),
        "light": light,
        "reason": reason,
        "fix": fix,
        "problems": [{"code": c, "text": text(c), "fix": _COPY[c][1]} for c in codes],
        "missing_scopes": missing,
        "orders_waiting": waiting,
        "tracking_failing_orders": failing,
        "last_order_at": last.isoformat() if last else None,
    }
