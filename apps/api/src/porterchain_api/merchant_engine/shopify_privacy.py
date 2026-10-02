"""Shopify buyer access and erasure. One request row, then a field wipe.

The merchant is the controller. This module does not email the buyer.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_models import Address, Order, Stop
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderSource, OrderState
from porterchain_api.merchant_engine.secrets import decrypt_signing_secret, encrypt_signing_secret
from porterchain_api.merchant_engine.shopify_urls import normalize_shop_domain
from porterchain_api.merchant_models import ShopifyDataSubjectRequest, ShopifyIngressDlq, ShopifyShop

logger = logging.getLogger(__name__)

RETENTION_DAYS = 730
DUE_DAYS = 30
_STREET_KEYS = {
    "formatted",
    "name",
    "phone",
    "address1",
    "address2",
    "company",
    "line1",
    "contact_name",
    "place_id",
}
_HOLD_TAX = frozenset({OrderState.INVOICED.value, OrderState.CLOSED.value})
_HOLD_CLAIM = frozenset(
    {
        OrderState.CLAIM_OPEN.value,
        OrderState.DAMAGED.value,
        OrderState.REFUNDED.value,
    }
)

DATA_ELEMENTS: list[dict[str, str | int]] = [
    {"field": "customer.email", "purpose": "deliver", "lawful_basis": "contract", "retention_days": RETENTION_DAYS},
    {"field": "customer.phone", "purpose": "deliver", "lawful_basis": "contract", "retention_days": RETENTION_DAYS},
    {"field": "customer.name", "purpose": "deliver", "lawful_basis": "contract", "retention_days": RETENTION_DAYS},
    {"field": "dropoff.formatted", "purpose": "deliver", "lawful_basis": "contract", "retention_days": RETENTION_DAYS},
    {"field": "dropoff.postal", "purpose": "invoice", "lawful_basis": "legal_obligation", "retention_days": RETENTION_DAYS},
    {"field": "amount_cents", "purpose": "invoice", "lawful_basis": "legal_obligation", "retention_days": RETENTION_DAYS},
]

SUBPROCESSORS: list[dict[str, str]] = [
    {"name": "Shopify", "purpose": "Store the order the merchant asked us to deliver", "region": "Outside Canada"},
    {"name": "Clerk", "purpose": "Merchant sign-in", "region": "Canada and the United States"},
    {"name": "Stripe", "purpose": "Merchant charges", "region": "Outside Canada"},
    {"name": "Database host", "purpose": "Store the delivery record", "region": "Canada"},
    {"name": "Fleetbase", "purpose": "Dispatch a stop when the order was released", "region": "Canada"},
    {"name": "Mailer", "purpose": "Tell the merchant a privacy file is ready", "region": "Canada"},
]


def normalize_phone(raw: str | None) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 10:
        digits = f"1{digits}"
    if not digits:
        return ""
    return f"+{digits}"


def _hash(value: str) -> str | None:
    text = value.strip().lower()
    if not text:
        return None
    return hashlib.sha256(text.encode()).hexdigest()


def _payload(raw_body: bytes) -> dict[str, Any]:
    try:
        body = json.loads(raw_body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return body if isinstance(body, dict) else {}


def _order_ids(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("orders_to_redact")
    if not isinstance(raw, list):
        raw = payload.get("orders_requested")
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        if isinstance(item, dict):
            value = item.get("id") or item.get("order_id")
        else:
            value = item
        text = str(value or "").strip()
        if text:
            out.append(text)
    return out


def open_privacy_request(
    db: Session,
    *,
    topic: str,
    shop: ShopifyShop | None,
    raw_body: bytes,
    webhook_id: str | None,
) -> dict[str, Any]:
    """Insert the case. The HTTP reply must not contain buyer contact."""
    payload = _payload(raw_body)
    webhook_key = (webhook_id or "").strip() or hashlib.sha256(raw_body).hexdigest()
    existing = (
        db.query(ShopifyDataSubjectRequest)
        .filter(ShopifyDataSubjectRequest.shopify_webhook_id == webhook_key)
        .first()
    )
    if existing is not None:
        if existing.status == "received":
            return {"ok": True, "request_id": existing.id, "retry": True}
        return {"ok": True, "duplicate": True}

    customer = payload.get("customer") if isinstance(payload.get("customer"), dict) else {}
    email = str(customer.get("email") or "").strip().lower()
    phone = normalize_phone(str(customer.get("phone") or ""))
    shop_domain = normalize_shop_domain(
        str(payload.get("shop_domain") or (shop.shop_domain if shop else "") or "")
    )
    if shop is None and shop_domain:
        shop = db.query(ShopifyShop).filter(ShopifyShop.shop_domain == shop_domain).first()
    now = datetime.now(UTC)
    row = ShopifyDataSubjectRequest(
        shop_id=shop.id if shop else None,
        merchant_id=shop.merchant_id if shop else None,
        topic=topic,
        shopify_webhook_id=webhook_key,
        shopify_customer_id=str(customer.get("id") or "") or None,
        email_hash=_hash(email),
        phone_hash=_hash(phone),
        orders_requested=_order_ids(payload),
        status="received",
        due_at=now + timedelta(days=DUE_DAYS),
        orders_touched=0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"ok": True, "request_id": row.id}


def accept_and_enqueue(
    db: Session,
    *,
    topic: str,
    shop: ShopifyShop | None,
    raw_body: bytes,
    webhook_id: str | None,
    remember,
) -> dict[str, Any]:
    opened = open_privacy_request(
        db, topic=topic, shop=shop, raw_body=raw_body, webhook_id=webhook_id
    )
    if opened.get("duplicate"):
        return {"ok": True, "duplicate": True}
    request_id = opened.get("request_id")
    if request_id:
        try:
            from porterchain_shared.queue.names import QueueName
            from porterchain_shared.queue.publisher import get_queue_publisher

            get_queue_publisher().enqueue(
                QueueName.WEBHOOKS,
                {"action": "shopify_privacy", "request_id": request_id},
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("shopify_privacy_enqueue_failed")
            raise RuntimeError("shopify_enqueue_failed") from exc
    remember()
    return {"ok": True}


def process_privacy_request(db: Session, settings: Settings, request_id: str) -> dict[str, Any]:
    row = db.get(ShopifyDataSubjectRequest, request_id)
    if row is None:
        return {"ok": False, "missing": True}
    if row.status not in {"received", "running"}:
        return {"ok": True, "duplicate": True, "status": row.status}
    row.status = "running"
    db.commit()

    shop = db.get(ShopifyShop, row.shop_id) if row.shop_id else None
    if row.topic == "customers/data_request":
        export = _export_orders(db, row, shop)
        row.export_ciphertext = encrypt_signing_secret(
            json.dumps(export), encryption_key=settings.jwt_secret
        )
        row.orders_touched = len(export)
        row.status = "fulfilled"
        row.hold_reason = None
    elif row.topic in {"customers/redact", "shop/redact"}:
        if row.topic == "shop/redact" and shop is not None:
            shop.uninstalled_at = datetime.now(UTC)
            shop.encrypted_access_token = None
            shop.encrypted_webhook_secret = None
            shop.default_pickup_address_id = None
        touched, reason = _redact_orders(db, settings, row, shop)
        row.orders_touched = touched
        row.hold_reason = reason
        row.status = "partial_hold" if reason else "fulfilled"
    else:
        row.status = "fulfilled"
    row.fulfilled_at = datetime.now(UTC)
    db.commit()
    return {"ok": True, "status": row.status, "orders": row.orders_touched}


def list_requests(db: Session, merchant_id: str) -> list[dict[str, Any]]:
    rows = (
        db.query(ShopifyDataSubjectRequest)
        .filter(ShopifyDataSubjectRequest.merchant_id == merchant_id)
        .order_by(ShopifyDataSubjectRequest.created_at.desc())
        .limit(100)
        .all()
    )
    return [_public_row(row) for row in rows]


def export_for_merchant(
    db: Session, settings: Settings, *, merchant_id: str, request_id: str
) -> dict[str, Any] | None:
    row = db.get(ShopifyDataSubjectRequest, request_id)
    if row is None or row.merchant_id != merchant_id or not row.export_ciphertext:
        return None
    raw = decrypt_signing_secret(row.export_ciphertext, encryption_key=settings.jwt_secret)
    body = json.loads(raw)
    return body if isinstance(body, dict) else {"orders": body}


def run_retention(db: Session, settings: Settings, *, limit: int = 100) -> dict[str, int]:
    cutoff = datetime.now(UTC) - timedelta(days=RETENTION_DAYS)
    orders = (
        db.query(Order)
        .filter(
            Order.order_source == OrderSource.SHOPIFY.value,
            Order.state.in_([OrderState.DELIVERED.value, OrderState.CLOSED.value]),
            Order.created_at < cutoff,
        )
        .order_by(Order.created_at.asc())
        .limit(limit)
        .all()
    )
    wiped = 0
    for order in orders:
        meta = _shopify_meta(order)
        customer = meta.get("customer") if isinstance(meta.get("customer"), dict) else {}
        if customer.get("redacted_at"):
            continue
        _wipe_order(db, settings, order, hold=False)
        wiped += 1
    if wiped:
        db.commit()
    return {"wiped": wiped, "scanned": len(orders)}


def _public_row(row: ShopifyDataSubjectRequest) -> dict[str, Any]:
    return {
        "id": row.id,
        "topic": row.topic,
        "status": row.status,
        "received_at": row.created_at.isoformat() if row.created_at else None,
        "due_at": row.due_at.isoformat() if row.due_at else None,
        "orders_touched": row.orders_touched,
        "hold_reason": row.hold_reason,
        "download": row.topic == "customers/data_request" and row.status == "fulfilled",
    }


def _export_orders(
    db: Session, row: ShopifyDataSubjectRequest, shop: ShopifyShop | None
) -> dict[str, Any]:
    orders = _matched_orders(db, row, shop)
    items = []
    for order in orders:
        dropoff = order.dropoff if isinstance(order.dropoff, dict) else {}
        pickup = order.pickup if isinstance(order.pickup, dict) else {}
        meta = _shopify_meta(order)
        customer = meta.get("customer") if isinstance(meta.get("customer"), dict) else {}
        items.append(
            {
                "order_id": order.id,
                "shopify_order_id": meta.get("order_id"),
                "tracking_number": order.tracking_number,
                "pickup_postal": pickup.get("postal"),
                "dropoff_postal": dropoff.get("postal"),
                "dropoff_city": dropoff.get("city"),
                "amount_cents": order.amount_cents,
                "currency": order.currency,
                "state": order.state,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "customer": {
                    "id": customer.get("id"),
                    "email": customer.get("email"),
                    "phone": customer.get("phone"),
                    "name": customer.get("name"),
                    "purpose": customer.get("purpose") or "deliver",
                    "lawful_basis": customer.get("lawful_basis") or "contract",
                },
            }
        )
    return {"orders": items}


def _redact_orders(
    db: Session,
    settings: Settings,
    row: ShopifyDataSubjectRequest,
    shop: ShopifyShop | None,
) -> tuple[int, str | None]:
    if row.topic == "shop/redact":
        orders = _shop_orders(db, shop)
    else:
        orders = _matched_orders(db, row, shop)
    reason: str | None = None
    for order in orders:
        hold = _hold_reason(db, order)
        if hold and reason is None:
            reason = hold
        _wipe_order(db, settings, order, hold=bool(hold))
        _clear_dlq(db, _shopify_meta(order).get("order_id"))
    return len(orders), reason


def _matched_orders(
    db: Session, row: ShopifyDataSubjectRequest, shop: ShopifyShop | None
) -> list[Order]:
    if shop is None or shop.merchant_id is None:
        return []
    wanted = {str(item) for item in (row.orders_requested or [])}
    email_hash = row.email_hash
    phone_hash = row.phone_hash
    customer_id = (row.shopify_customer_id or "").strip()
    found: list[Order] = []
    for order in _shop_orders(db, shop):
        meta = _shopify_meta(order)
        shopify_order_id = str(meta.get("order_id") or "")
        customer = meta.get("customer") if isinstance(meta.get("customer"), dict) else {}
        if wanted and shopify_order_id in wanted:
            found.append(order)
            continue
        if customer_id and str(customer.get("id") or "") == customer_id:
            found.append(order)
            continue
        stored_email = str(customer.get("email") or "").strip().lower()
        if email_hash and _hash(stored_email) == email_hash:
            found.append(order)
            continue
        stored_phone = normalize_phone(str(customer.get("phone") or ""))
        if phone_hash and _hash(stored_phone) == phone_hash:
            found.append(order)
    if wanted:
        by_id = [order for order in found if str(_shopify_meta(order).get("order_id") or "") in wanted]
        return by_id or found
    return found


def _shop_orders(db: Session, shop: ShopifyShop | None) -> list[Order]:
    if shop is None:
        return []
    rows = (
        db.query(Order)
        .filter(Order.merchant_id == shop.merchant_id)
        .order_by(Order.created_at.asc())
        .all()
    )
    domain = shop.shop_domain
    out: list[Order] = []
    for order in rows:
        meta = _shopify_meta(order)
        if order.order_source == OrderSource.SHOPIFY.value or meta.get("shop_domain") == domain:
            out.append(order)
    return out


def _wipe_order(db: Session, settings: Settings, order: Order, *, hold: bool) -> None:
    if isinstance(order.dropoff, dict):
        order.dropoff = _wipe_address(order.dropoff, hold=hold)
    order.special_instructions = None
    meta = dict(order.compliance_metadata or {})
    shopify_meta = dict(meta.get("shopify") or {})
    customer = shopify_meta.get("customer") if isinstance(shopify_meta.get("customer"), dict) else {}
    shopify_meta["customer"] = {
        "id": customer.get("id"),
        "email": None,
        "phone": None,
        "name": None,
        "purpose": "deliver",
        "lawful_basis": "contract",
        "redacted_at": datetime.now(UTC).isoformat(),
    }
    meta["shopify"] = shopify_meta
    order.compliance_metadata = meta
    db.add(order)
    for stop in db.query(Stop).filter(Stop.order_id == order.id).all():
        if stop.kind not in {"drop", "dropoff"} or not stop.address_id:
            continue
        address = db.get(Address, stop.address_id)
        if address is None:
            continue
        address.formatted = "redacted"
        address.line1 = None
        address.contact_name = None
        address.phone = None
        address.place_id = None
        if not hold:
            compact = (address.postal or "").replace(" ", "")
            address.postal = compact[:3] or None
            address.lat = None
            address.lng = None
    if order.fleetbase_order_id:
        try:
            from porterchain_api.merchant_engine.booking_service import push_redacted_order

            push_redacted_order(db, settings, order)
        except Exception:
            logger.exception("shopify_privacy_fleetbase_sync_failed order=%s", order.id)


def _wipe_address(addr: dict[str, Any], *, hold: bool) -> dict[str, Any]:
    out = dict(addr)
    for key in _STREET_KEYS:
        if key in out:
            out[key] = None
    if not hold:
        postal = str(out.get("postal") or out.get("zip") or "")
        compact = postal.replace(" ", "")
        fsa = compact[:3] or None
        out["postal"] = fsa
        if "zip" in out:
            out["zip"] = fsa
        out["lat"] = None
        out["lng"] = None
    out["redacted_at"] = datetime.now(UTC).isoformat()
    return out


def _clear_dlq(db: Session, shopify_order_id: Any) -> None:
    text = str(shopify_order_id or "").strip()
    if not text:
        return
    rows = (
        db.query(ShopifyIngressDlq)
        .filter(ShopifyIngressDlq.shopify_order_id == text)
        .all()
    )
    for row in rows:
        row.raw_body = ""
        row.detail = "redacted"


def _hold_reason(db: Session, order: Order) -> str | None:
    from porterchain_api.merchant_engine.shopify_claim_hold import open_payment_dispute

    if open_payment_dispute(db, order.id):
        return "chargeback"
    if order.state in _HOLD_CLAIM:
        return "claim"
    if order.state in _HOLD_TAX:
        return "tax"
    return None


def _shopify_meta(order: Order) -> dict[str, Any]:
    meta = (order.compliance_metadata or {}).get("shopify")
    return meta if isinstance(meta, dict) else {}
