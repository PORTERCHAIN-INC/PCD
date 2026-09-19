"""Email the receiver the public website track link — not the merchant portal."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.tracking_service import public_track_url
from porterchain_api.merchant_models import MerchantRecipient
from porterchain_api.booking_models import Order
from porterchain_api.schemas_merchant import MerchantBookDeliveryRequest

logger = logging.getLogger(__name__)

_EMAIL_ERRORS = {
    "consignee_email_required": "Add a receiver email to send tracking.",
    "consignee_email_invalid": "That receiver email does not look valid.",
    "order_not_found": "That order was not found.",
}


def consignee_error_message(code: str) -> str:
    return _EMAIL_ERRORS.get(code, _EMAIL_ERRORS["consignee_email_required"])


def _clean_email(value: str | None) -> str | None:
    raw = (value or "").strip()
    if not raw or "@" not in raw or "." not in raw.split("@")[-1]:
        return None
    return raw


def resolve_consignee_email(
    db: Session,
    ctx: MerchantContext,
    body: MerchantBookDeliveryRequest,
) -> str | None:
    direct = _clean_email(getattr(body, "consignee_email", None))
    if direct:
        return direct
    if not body.recipient_id:
        return None
    record = (
        db.query(MerchantRecipient)
        .filter(
            MerchantRecipient.id == body.recipient_id,
            MerchantRecipient.merchant_id == ctx.merchant.id,
        )
        .first()
    )
    return _clean_email(record.email if record else None)


def consignee_email_from_order(order: Order) -> str | None:
    meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
    block = meta.get("consignee") if isinstance(meta.get("consignee"), dict) else {}
    return _clean_email(block.get("email") if isinstance(block, dict) else None)


def store_consignee_email(order: Order, email: str) -> None:
    meta = dict(order.compliance_metadata or {})
    block = dict(meta.get("consignee") or {})
    block["email"] = email
    meta["consignee"] = block
    order.compliance_metadata = meta


def send_consignee_tracking(
    db: Session,
    settings: Settings,
    order: Order,
    email: str,
    *,
    merchant_name: str | None = None,
) -> dict[str, Any]:
    from porterchain_api.domain.sandbox import order_is_sandbox

    if order_is_sandbox(order):
        raise ValueError("sandbox_orders_have_no_public_track")
    url = public_track_url(settings, order.tracking_number, is_sandbox=False)
    from porterchain_api.notification_engine.orchestrator import NotificationOrchestrator

    NotificationOrchestrator().send_consignee_tracking(
        db,
        email=email,
        tracking_number=order.tracking_number or "",
        order_number=order.order_number or "",
        public_track_url=url or "",
        merchant_name=merchant_name or "",
        correlation_id=f"{order.id}:{uuid4().hex[:8]}",
    )
    return {"sent": True, "email": email, "public_track_url": url}


def send_consignee_tracking_safe(
    db: Session,
    settings: Settings,
    order: Order,
    email: str,
    *,
    merchant_name: str | None = None,
) -> None:
    try:
        send_consignee_tracking(db, settings, order, email, merchant_name=merchant_name)
    except Exception:  # noqa: BLE001
        logger.exception("consignee tracking email failed for order %s", order.id)
