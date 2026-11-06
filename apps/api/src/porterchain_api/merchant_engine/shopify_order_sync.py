"""Shopify order sync ledger (App Store review 139170, requirement 2.1.4).

Root cause of the review failure: an order whose buyer picked a store shipping rate
(e.g. "Standard") or an address outside the service area was dropped silently
(`skipped: not_porterchain_rate` / `out_of_service_area`) and Shopify test orders were
booked as sandbox rows hidden by the Orders "Live only" filter. Nothing told the
merchant the order existed, so the app looked like it never synced.

Now every order Shopify sends us (webhook) or that we find by polling (reconcile) gets
one ``ShopifyOrderSync`` row with items, address, totals and what happened. Unbooked
orders can be booked from the portal with one click.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.integrations.shopify_orders import (
    customer_slice,
    format_shopify_address,
    line_item_slice,
    order_ids,
    shipping_address,
)
from porterchain_api.merchant_models import ShopifyOrderSync, ShopifyShop

logger = logging.getLogger("porterchain.shopify_order_sync")

REASON_TEXT = {
    "not_porterchain_rate": "Buyer chose a different shipping rate at checkout. Book it with PorterChain if you want us to deliver it.",
    "out_of_service_area": "Delivery address is outside the PorterChain service area.",
    "unpaid": "Order is not paid yet. It will book when Shopify marks it paid.",
    "ingress_paused": "Order intake is paused for this store.",
    "shopify_billing_not_approved": "Approve PorterChain charges in Shopify (Apps > PorterChain) to book deliveries.",
    "default_pickup_required": "Set a pickup address in PorterChain to book Shopify orders.",
    "merchant_not_active": "Your PorterChain account is not active yet.",
    "shipping_address_required": "Order has no shipping address.",
    "cancelled": "Order was cancelled in Shopify.",
    "address_needs_review": "We can't confidently place this delivery address. Pick the right address to book it.",
    "shopify_billing_cap_reached": "Your monthly PorterChain limit in Shopify is used up. Raise it in Apps > PorterChain to book.",
}


def _cents(value: Any) -> int | None:
    try:
        return int((Decimal(str(value)) * 100).quantize(Decimal("1")))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _when(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")) if value else None
    except ValueError:
        return None


def _items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    out = line_item_slice(payload)
    raw = payload.get("line_items") if isinstance(payload.get("line_items"), list) else []
    for row, src in zip(out, raw, strict=False):
        if isinstance(src, dict):
            row["price_cents"] = _cents(src.get("price"))
            row["grams"] = src.get("grams")
    return out


def classify(result: dict[str, Any] | None, exc: BaseException | None = None) -> tuple[str, str | None, str | None]:
    """(status, reason_code, porterchain_order_id) from a book/update/cancel result."""
    if exc is not None:
        code = str(getattr(exc, "code", "") or exc) or type(exc).__name__
        code = code if code in REASON_TEXT else ("error" if len(code) > 60 else code)
        return "error", code, None
    r = result or {}
    if r.get("order_id") and not r.get("skipped"):
        return ("cancelled" if r.get("cancelled") else "booked"), None, str(r["order_id"])
    skipped = r.get("skipped")
    if skipped == "order_not_found":
        return "not_booked", None, None
    if skipped:
        return "not_booked", str(skipped), (str(r["order_id"]) if r.get("order_id") else None)
    return "not_booked", None, None


def record(
    db: Session,
    shop: ShopifyShop,
    payload: dict[str, Any],
    *,
    action: str,
    result: dict[str, Any] | None = None,
    exc: BaseException | None = None,
    source: str = "webhook",
) -> ShopifyOrderSync | None:
    """Upsert the ledger row. Never raises (sync bookkeeping must not drop a booking)."""
    try:
        order_id, name = order_ids(payload)
        if not order_id:
            return None
        row = (
            db.query(ShopifyOrderSync)
            .filter_by(shop_domain=shop.shop_domain, shopify_order_id=order_id)
            .first()
        )
        if row is None:
            row = ShopifyOrderSync(merchant_id=shop.merchant_id, shop_domain=shop.shop_domain, shopify_order_id=order_id)
            db.add(row)
        status, reason, pc_id = classify(result, exc)
        if action == "shopify_orders_cancelled" or payload.get("cancelled_at"):
            status, reason = "cancelled", "cancelled"
        # Never downgrade a booked row because a later update was skipped.
        if not (row.status == "booked" and status == "not_booked" and action != "shopify_orders_create"):
            row.status = status
            row.reason_code = reason
        if pc_id:
            row.porterchain_order_id = pc_id
        row.merchant_id = shop.merchant_id
        row.order_name = name or row.order_name
        if "line_items" in payload or "shipping_address" in payload:  # orders/delete sends only the id
            row.is_test = bool(payload.get("test"))
            row.financial_status = str(payload.get("financial_status") or "") or row.financial_status
            lines = payload.get("shipping_lines") if isinstance(payload.get("shipping_lines"), list) else []
            if lines and isinstance(lines[0], dict):
                row.shipping_title = str(lines[0].get("title") or "")[:255] or None
                row.shipping_cents = _cents(lines[0].get("price"))
            addr = shipping_address(payload)
            row.ship_to = format_shopify_address(addr) if addr else None
            row.customer_name = customer_slice(payload).get("name")
            row.line_items = _items(payload)
            row.currency = str(payload.get("currency") or "") or None
            row.subtotal_cents = _cents(payload.get("subtotal_price"))
            row.total_cents = _cents(payload.get("total_price"))
            row.shopify_created_at = _when(payload.get("created_at")) or row.shopify_created_at
        if row.source != "webhook":
            row.source = source
        db.commit()
        return row
    except Exception:  # noqa: BLE001
        db.rollback()
        logger.exception("shopify_order_sync_record_failed shop=%s", shop.shop_domain)
        return None


def serialize(row: ShopifyOrderSync) -> dict[str, Any]:
    return {
        "id": row.id,
        "shop_domain": row.shop_domain,
        "shopify_order_id": row.shopify_order_id,
        "order_name": row.order_name,
        "status": row.status,
        "reason_code": row.reason_code,
        "reason": REASON_TEXT.get(row.reason_code or "", row.reason_code),
        "is_test": row.is_test,
        "financial_status": row.financial_status,
        "shipping_title": row.shipping_title,
        "ship_to": row.ship_to,
        "customer_name": row.customer_name,
        "line_items": row.line_items or [],
        "currency": row.currency,
        "subtotal_cents": row.subtotal_cents,
        "shipping_cents": row.shipping_cents,
        "total_cents": row.total_cents,
        "porterchain_order_id": row.porterchain_order_id,
        "tracking_number": None,
        "source": row.source,
        "needs_address_review": row.status == "not_booked" and row.reason_code == "address_needs_review",
        "can_book": row.status in {"not_booked", "error"} and row.reason_code not in {"cancelled", "ingress_paused"},
        "shopify_created_at": row.shopify_created_at.isoformat() if row.shopify_created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def list_for_merchant(db: Session, merchant_id: str, *, q: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    query = db.query(ShopifyOrderSync).filter(ShopifyOrderSync.merchant_id == merchant_id)
    if q:
        term = q.strip().lstrip("#")
        like = f"%{term}%"
        query = query.filter(
            (ShopifyOrderSync.order_name.ilike(like))
            | (ShopifyOrderSync.shopify_order_id.ilike(like))
            | (ShopifyOrderSync.customer_name.ilike(like))
        )
    rows = query.order_by(ShopifyOrderSync.shopify_created_at.desc().nullslast(), ShopifyOrderSync.created_at.desc()).limit(limit).all()
    out = [serialize(r) for r in rows]
    ids = [r["porterchain_order_id"] for r in out if r["porterchain_order_id"]]
    if ids:
        from porterchain_api.booking_models import Order

        found = dict(db.query(Order.id, Order.tracking_number).filter(Order.id.in_(ids)).all())
        for r in out:
            r["tracking_number"] = found.get(r["porterchain_order_id"])
    return out


# ---------- reconcile (missed webhooks, reinstall) ----------

_ORDER_FIELDS = """
      legacyResourceId name email test createdAt cancelledAt displayFinancialStatus
      currencyCode
      subtotalPriceSet { shopMoney { amount } }
      totalPriceSet { shopMoney { amount } }
      shippingLines(first: 5) { nodes { title code source originalPriceSet { shopMoney { amount } } } }
      shippingAddress { firstName lastName name address1 address2 city provinceCode zip countryCodeV2 phone latitude longitude }
      lineItems(first: 50) { nodes { title sku quantity originalUnitPriceSet { shopMoney { amount } }__WEIGHT__ } }
"""
# Buyer name comes from the shipping address: `customer` needs read_customers, which the
# app does not ask for (minimum scopes). Weight needs read_products/read_inventory on some
# installs, so it is asked for first and dropped on ACCESS_DENIED.
_WEIGHT = " variant { inventoryItem { measurement { weight { value unit } } } }"
_ORDERS_TMPL = (
    "query Recent($q: String!, $after: String) { orders(first: 50, after: $after, query: $q, sortKey: CREATED_AT) {"
    " pageInfo { hasNextPage endCursor } nodes {" + _ORDER_FIELDS + "} } }"
)
_ORDER_TMPL = "query One($id: ID!) { order(id: $id) {" + _ORDER_FIELDS + "} }"
_ORDERS_Q = _ORDERS_TMPL.replace("__WEIGHT__", _WEIGHT)
_ORDER_Q = _ORDER_TMPL.replace("__WEIGHT__", _WEIGHT)


def _gql(shop_domain: str, token: str, settings: Settings, tmpl: str, variables: dict[str, Any]) -> dict[str, Any]:
    from porterchain_api.merchant_engine.shopify_admin_graphql import ShopifyAdminError, admin_graphql

    try:
        return admin_graphql(shop_domain, token, settings, tmpl.replace("__WEIGHT__", _WEIGHT), variables)
    except ShopifyAdminError as exc:
        if "ACCESS_DENIED" not in str(exc):
            raise
        return admin_graphql(shop_domain, token, settings, tmpl.replace("__WEIGHT__", ""), variables)

_TO_GRAMS = {"GRAMS": 1.0, "KILOGRAMS": 1000.0, "POUNDS": 453.592, "OUNCES": 28.3495}


def rest_shape(node: dict[str, Any]) -> dict[str, Any]:
    """GraphQL order -> the REST webhook shape the booking code already understands."""
    def money(block: Any) -> Any:
        return ((block or {}).get("shopMoney") or {}).get("amount")

    addr = node.get("shippingAddress") or None
    items = []
    for li in ((node.get("lineItems") or {}).get("nodes") or []):
        w = (((li.get("variant") or {}).get("inventoryItem") or {}).get("measurement") or {}).get("weight") or {}
        grams = None
        if w.get("value") is not None:
            grams = round(float(w["value"]) * _TO_GRAMS.get(str(w.get("unit")), 1.0))
        items.append({"title": li.get("title"), "sku": li.get("sku"), "quantity": li.get("quantity"),
                      "price": money(li.get("originalUnitPriceSet")), "grams": grams, "requires_shipping": True})
    lines = [{"title": s.get("title"), "code": s.get("code"), "source": s.get("source"),
              "price": money(s.get("originalPriceSet"))}
             for s in ((node.get("shippingLines") or {}).get("nodes") or [])]
    cust = {"firstName": (addr or {}).get("firstName"), "lastName": (addr or {}).get("lastName")} if addr else {}
    return {
        "id": node.get("legacyResourceId"),
        "name": node.get("name"),
        "email": node.get("email"),
        "test": bool(node.get("test")),
        "created_at": node.get("createdAt"),
        "cancelled_at": node.get("cancelledAt"),
        "financial_status": str(node.get("displayFinancialStatus") or "").lower(),
        "currency": node.get("currencyCode"),
        "subtotal_price": money(node.get("subtotalPriceSet")),
        "total_price": money(node.get("totalPriceSet")),
        "shipping_lines": lines,
        "line_items": items,
        "customer": {"id": cust.get("legacyResourceId"), "first_name": cust.get("firstName"), "last_name": cust.get("lastName")} if cust else None,
        "shipping_address": None if not addr else {
            "first_name": addr.get("firstName"), "last_name": addr.get("lastName"), "name": addr.get("name"),
            "address1": addr.get("address1"), "address2": addr.get("address2"), "city": addr.get("city"),
            "province_code": addr.get("provinceCode"), "zip": addr.get("zip"), "country_code": addr.get("countryCodeV2"),
            "phone": addr.get("phone"), "latitude": addr.get("latitude"), "longitude": addr.get("longitude"),
        },
    }


def fetch_recent(shop: ShopifyShop, settings: Settings, *, since: datetime) -> list[dict[str, Any]]:
    from porterchain_api.merchant_engine.shopify_tokens import access_token_for

    token = access_token_for(shop, settings)
    if not token:
        raise RuntimeError("missing_access_token")
    out: list[dict[str, Any]] = []
    after = None
    q = f"created_at:>='{since.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}'"
    for _ in range(10):  # max 500 orders per run
        data = _gql(shop.shop_domain, token, settings, _ORDERS_TMPL, {"q": q, "after": after})
        block = data.get("orders") or {}
        out += [rest_shape(n) for n in block.get("nodes") or []]
        page = block.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            break
        after = page.get("endCursor")
    return out


def reconcile_shop(db: Session, settings: Settings, shop: ShopifyShop, *, days: int = 3) -> dict[str, int]:
    """Pull recent orders and process any we never recorded (missed webhook / reinstall)."""
    from porterchain_api.merchant_engine.shopify_webhooks import process_order_payload

    since = datetime.now(UTC) - timedelta(days=days)
    orders = fetch_recent(shop, settings, since=since)
    known = {
        r[0]
        for r in db.query(ShopifyOrderSync.shopify_order_id).filter(ShopifyOrderSync.shop_domain == shop.shop_domain).all()
    }
    found = new = 0
    for payload in orders:
        found += 1
        oid = str(payload.get("id") or "")
        if not oid or oid in known:
            continue
        new += 1
        action = "shopify_orders_cancelled" if payload.get("cancelled_at") else "shopify_orders_create"
        try:
            process_order_payload(db, settings, shop_domain=shop.shop_domain, action=action, body=payload, source="reconcile")
        except Exception:  # noqa: BLE001 — recorded as error row; keep going
            db.rollback()
            logger.exception("shopify_reconcile_order_failed shop=%s order=%s", shop.shop_domain, oid)
    shop.last_reconciled_at = datetime.now(UTC)
    db.commit()
    return {"found": found, "new": new}


def reconcile_all(db: Session, settings: Settings) -> dict[str, int]:
    total = {"shops": 0, "found": 0, "new": 0, "failed": 0}
    for shop in db.query(ShopifyShop).filter(ShopifyShop.uninstalled_at.is_(None)).all():
        if not shop.encrypted_access_token:
            continue
        total["shops"] += 1
        try:
            r = reconcile_shop(db, settings, shop)
            total["found"] += r["found"]
            total["new"] += r["new"]
        except Exception:  # noqa: BLE001
            db.rollback()
            total["failed"] += 1
            logger.warning("shopify_reconcile_failed shop=%s", shop.shop_domain, exc_info=True)
    return total


def _fetch_payload(db: Session, settings: Settings, merchant_id: str, sync_id: str) -> tuple[ShopifyOrderSync, ShopifyShop, dict[str, Any]]:
    from porterchain_api.merchant_engine.shopify_tokens import access_token_for

    row = db.query(ShopifyOrderSync).filter_by(id=sync_id, merchant_id=merchant_id).first()
    if row is None:
        raise LookupError("shopify_order_not_found")
    shop = db.query(ShopifyShop).filter(ShopifyShop.shop_domain == row.shop_domain, ShopifyShop.uninstalled_at.is_(None)).first()
    if shop is None:
        raise LookupError("shop_not_connected")
    token = access_token_for(shop, settings)
    if not token:
        raise RuntimeError("missing_access_token")
    data = _gql(shop.shop_domain, token, settings, _ORDER_TMPL, {"id": f"gid://shopify/Order/{row.shopify_order_id}"})
    node = data.get("order")
    if not node:
        raise LookupError("shopify_order_not_found")
    return row, shop, rest_shape(node)


def address_candidates(db: Session, settings: Settings, merchant_id: str, sync_id: str) -> dict[str, Any]:
    """Resolver candidates for a held order (AddressDisambiguationModal feed)."""
    from porterchain_api.merchant_engine.shopify_address_review import resolve_shipping

    row, _shop, payload = _fetch_payload(db, settings, merchant_id, sync_id)
    addr = shipping_address(payload) or {}
    if not addr:
        raise LookupError("shipping_address_required")
    return {"sync_id": row.id, "original_address": format_shopify_address(addr), **resolve_shipping(addr)}


def book_now(
    db: Session,
    settings: Settings,
    merchant_id: str,
    sync_id: str,
    *,
    lat: float | None = None,
    lng: float | None = None,
) -> dict[str, Any]:
    """Merchant clicked "Book with PorterChain" (other rate, or a held address they fixed).

    ``lat``/``lng`` = the point the merchant picked in the address review popup.
    """
    from porterchain_api.merchant_engine.shopify_address_review import apply_choice
    from porterchain_api.merchant_engine.shopify_webhooks import process_order_payload

    row, shop, payload = _fetch_payload(db, settings, merchant_id, sync_id)
    if lat is not None and lng is not None:
        payload = apply_choice(payload, lat=lat, lng=lng)
    payload["_force_book"] = True
    return process_order_payload(db, settings, shop_domain=shop.shop_domain, action="shopify_orders_create", body=payload, source=row.source)


def reconcile_merchant(db: Session, settings: Settings, merchant_id: str, *, days: int = 7) -> dict[str, int] | None:
    """"Sync now" for every connected store of one merchant. None = no connected store."""
    shops = (
        db.query(ShopifyShop)
        .filter(ShopifyShop.merchant_id == merchant_id, ShopifyShop.uninstalled_at.is_(None))
        .all()
    )
    if not shops:
        return None
    total: dict[str, int] = {}
    for shop in shops:
        for k, v in reconcile_shop(db, settings, shop, days=days).items():
            total[k] = total.get(k, 0) + int(v or 0)
    return total
