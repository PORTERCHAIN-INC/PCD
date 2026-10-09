"""Shopify ingress DLQ — record failures / soft-holds for admin replay."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.integrations.shopify_orders import order_ids
from porterchain_api.merchant_models import ShopifyIngressDlq, ShopifyShop

logger = logging.getLogger(__name__)

# Stable reason codes for admin filters / CT later.
REASON_INGRESS_PAUSED = "ingress_paused"
REASON_MISSING_PICKUP = "missing_pickup"
REASON_MERCHANT_INACTIVE = "merchant_inactive"
REASON_SHOP_NOT_CONNECTED = "shop_not_connected"
REASON_ONTARIO = "ontario"
REASON_CREDIT = "credit"
REASON_HMAC = "hmac"
REASON_PAYLOAD = "payload_invalid"
REASON_WORKER = "worker_error"
REASON_BOOKING = "booking_rejected"


def _is_booking_validation_error(exc: BaseException) -> bool:
    """Duck-type Fleetbase BookingValidationError without a cross-engine import."""
    return type(exc).__name__ == "BookingValidationError"


def reason_from_exc(exc: BaseException) -> tuple[str, str]:
    """Map book/cancel exceptions → (reason_code, detail)."""
    msg = str(exc) or exc.__class__.__name__
    code = msg.split(":", 1)[0].strip() if msg else ""
    lowered = msg.lower()
    if isinstance(exc, LookupError) or code in {"shop_not_connected", "merchant_not_found"}:
        return REASON_SHOP_NOT_CONNECTED, msg
    if code == "default_pickup_required" or "pickup" in lowered and "required" in lowered:
        return REASON_MISSING_PICKUP, msg
    if code == "merchant_not_active":
        return REASON_MERCHANT_INACTIVE, msg
    if "ontario" in lowered or "service_area" in lowered:
        return REASON_ONTARIO, msg
    if "credit" in lowered or "headroom" in lowered:
        return REASON_CREDIT, msg
    if "hmac" in lowered:
        return REASON_HMAC, msg
    if _is_booking_validation_error(exc):
        return REASON_BOOKING, f"{getattr(exc, 'code', '')}: {msg}".strip(": ")
    if code == "payload_invalid" or isinstance(exc, (ValueError, json.JSONDecodeError)):
        return REASON_PAYLOAD, msg
    return REASON_WORKER, msg


def purge_stale_dlq_bodies(db: Session, *, days: int = 14) -> None:
    """Drop raw webhook bodies after the retention window. The reason row stays."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    db.query(ShopifyIngressDlq).filter(
        ShopifyIngressDlq.created_at < cutoff,
        ShopifyIngressDlq.raw_body != "",
    ).update({ShopifyIngressDlq.raw_body: ""}, synchronize_session=False)


def record_ingress_dlq(
    db: Session,
    *,
    shop: ShopifyShop | None,
    shop_domain: str,
    action: str,
    topic: str | None,
    raw_body: str,
    reason_code: str,
    detail: str | None = None,
    status: str = "open",
    porterchain_order_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> ShopifyIngressDlq:
    shopify_order_id = None
    body = payload
    if body is None:
        try:
            parsed = json.loads(raw_body or "{}")
            body = parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            body = None
    if body:
        shopify_order_id, _ = order_ids(body)

    merchant_id = shop.merchant_id if shop else None
    if not merchant_id and shop is None:
        # Cannot persist without merchant — log only.
        logger.warning(
            "shopify_dlq_skip_no_merchant shop=%s reason=%s", shop_domain, reason_code
        )
        raise LookupError("shop_not_connected")

    row = ShopifyIngressDlq(
        merchant_id=merchant_id or shop.merchant_id,  # type: ignore[union-attr]
        shop_id=shop.id if shop else None,
        shop_domain=shop_domain,
        topic=topic,
        action=action,
        shopify_order_id=shopify_order_id or None,
        reason_code=reason_code,
        detail=(detail or "")[:4000] or None,
        raw_body=raw_body if isinstance(raw_body, str) else str(raw_body),
        status=status,
        attempts=0,
        porterchain_order_id=porterchain_order_id,
    )
    db.add(row)
    try:
        purge_stale_dlq_bodies(db)
    except Exception:  # noqa: BLE001
        logger.exception("shopify_dlq_purge_failed")
    db.commit()
    db.refresh(row)
    logger.info(
        "shopify_ingress_dlq id=%s reason=%s status=%s shop=%s shopify_order=%s",
        row.id,
        reason_code,
        status,
        shop_domain,
        shopify_order_id,
    )
    return row


def list_ingress_dlq(
    db: Session,
    merchant_id: str,
    *,
    status: str | None = None,
    limit: int = 50,
) -> list[ShopifyIngressDlq]:
    q = db.query(ShopifyIngressDlq).filter(ShopifyIngressDlq.merchant_id == merchant_id)
    if status:
        q = q.filter(ShopifyIngressDlq.status == status)
    return q.order_by(ShopifyIngressDlq.created_at.desc()).limit(min(limit, 200)).all()


def mark_dlq_resolved(
    db: Session,
    row: ShopifyIngressDlq,
    *,
    admin_id: str | None,
    porterchain_order_id: str | None = None,
) -> ShopifyIngressDlq:
    row.status = "resolved"
    row.raw_body = ""
    row.resolved_at = datetime.now(UTC)
    row.resolved_by_admin_id = admin_id
    if porterchain_order_id:
        row.porterchain_order_id = porterchain_order_id
    row.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(row)
    return row


def dlq_row_payload(row: ShopifyIngressDlq) -> dict[str, Any]:
    return {
        "id": row.id,
        "merchant_id": row.merchant_id,
        "shop_id": row.shop_id,
        "shop_domain": row.shop_domain,
        "topic": row.topic,
        "action": row.action,
        "shopify_order_id": row.shopify_order_id,
        "reason_code": row.reason_code,
        "detail": row.detail,
        "status": row.status,
        "attempts": row.attempts,
        "porterchain_order_id": row.porterchain_order_id,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
        "resolved_by_admin_id": row.resolved_by_admin_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
