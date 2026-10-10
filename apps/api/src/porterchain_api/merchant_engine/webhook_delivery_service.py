"""Deliver outbound merchant webhooks — HMAC-signed POST per SECURITY.md."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from porterchain_api.config import get_settings
from porterchain_api.db import SessionLocal
from porterchain_api.merchant_engine.secrets import decrypt_signing_secret
from porterchain_api.merchant_models import MerchantWebhook, MerchantWebhookDelivery
from porterchain_api.booking_models import Order

logger = logging.getLogger(__name__)

_BACKOFF_SECONDS = (1, 4, 16)


def deliver_merchant_fanout(payload: dict[str, Any]) -> None:
    """Process a webhooks-queue fanout job from the event bus."""
    envelope = payload.get("envelope") or {}
    event_type = payload.get("event_type") or envelope.get("event_type")
    if not event_type:
        logger.warning("merchant fanout missing event_type")
        return

    aggregate_id = envelope.get("aggregate_id")
    aggregate_type = envelope.get("aggregate_type")
    if aggregate_type != "order" or not aggregate_id:
        logger.debug("merchant fanout skipped: aggregate_type=%s", aggregate_type)
        return

    settings = get_settings()
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == aggregate_id).first()
        if not order or not order.merchant_id:
            logger.debug("merchant fanout: order %s not found or not merchant-owned", aggregate_id)
            return

        hooks = (
            db.query(MerchantWebhook)
            .filter(
                MerchantWebhook.merchant_id == order.merchant_id,
                MerchantWebhook.is_active.is_(True),
            )
            .all()
        )
        body = {
            "event_type": event_type,
            "order_id": order.id,
            "order_number": order.order_number,
            "tracking_number": order.tracking_number,
            "state": order.state,
            "merchant_id": order.merchant_id,
            "is_sandbox": bool(getattr(order, "is_sandbox", False)),
            "occurred_at": envelope.get("occurred_at"),
            "payload": envelope.get("payload") or {},
        }
        order_env = "sandbox" if body["is_sandbox"] else "production"
        for hook in hooks:
            hook_env = (getattr(hook, "environment", None) or "production").lower()
            if hook_env != order_env:
                continue
            if not _hook_matches_event(hook.events, event_type):
                continue
            if not hook.encrypted_signing_secret:
                logger.warning("merchant webhook %s missing signing secret — skipping", hook.id)
                continue
            try:
                signing_secret = decrypt_signing_secret(
                    hook.encrypted_signing_secret, encryption_key=settings.jwt_secret
                )
            except ValueError:
                logger.exception("merchant webhook %s secret decrypt failed", hook.id)
                continue
            _post_with_retries(db, hook, body, signing_secret)
    finally:
        db.close()


def deliver_webhook_payload(
    url: str,
    body: dict[str, Any],
    signing_secret: str,
) -> tuple[int | None, str, str | None]:
    """Single delivery attempt. Returns (status_code, response_text, error)."""
    body_bytes = json.dumps(body, separators=(",", ":"), default=str).encode()
    timestamp = int(time.time())
    signature = _sign_payload(body_bytes, timestamp, signing_secret)
    headers = {
        "Content-Type": "application/json",
        "X-Porterchain-Signature": signature,
        "X-Porterchain-Timestamp": str(timestamp),
    }
    from porterchain_api.platform.outbound_url import UnsafeUrl, assert_public_https_url

    try:
        assert_public_https_url(url)  # re-check at send time (DNS rebinding)
    except UnsafeUrl as exc:
        return None, "", str(exc)
    try:
        response = httpx.post(url, content=body_bytes, headers=headers, timeout=15.0, follow_redirects=False)
        return response.status_code, response.text[:2000], None
    except httpx.HTTPError as exc:
        return None, "", str(exc)


def log_delivery(
    db: Session,
    *,
    merchant_id: str,
    webhook_id: str,
    event_type: str,
    request_body: dict[str, Any],
    response_status: int | None,
    response_body: str | None,
    attempt: int,
    success: bool,
    error_message: str | None,
    duration_ms: int,
    next_retry_at: datetime | None = None,
) -> MerchantWebhookDelivery:
    row = MerchantWebhookDelivery(
        merchant_id=merchant_id,
        webhook_id=webhook_id,
        event_type=event_type,
        request_body=request_body,
        response_status=response_status,
        response_body=(response_body or "")[:2000] if response_body else None,
        attempt=attempt,
        success=success,
        error_message=error_message,
        duration_ms=duration_ms,
        next_retry_at=next_retry_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _hook_matches_event(subscribed: list[str] | None, event_type: str) -> bool:
    if not subscribed:
        return True
    for pattern in subscribed:
        if pattern == event_type:
            return True
        if pattern.endswith(".*"):
            prefix = pattern[:-1]
            if event_type.startswith(prefix):
                return True
        if pattern == "order.*" and event_type.startswith("order."):
            return True
    return False


def _sign_payload(body_bytes: bytes, timestamp: int, signing_secret: str) -> str:
    signed = f"{timestamp}.".encode() + body_bytes
    return hmac.new(signing_secret.encode(), signed, hashlib.sha256).hexdigest()


def _post_with_retries(
    db: Session,
    hook: MerchantWebhook,
    body: dict[str, Any],
    signing_secret: str,
) -> None:
    """Single delivery attempt — never sleep on the worker. Record next_retry_at on 5xx."""
    start = time.perf_counter()
    status, response_text, error = deliver_webhook_payload(hook.url, body, signing_secret)
    duration_ms = int((time.perf_counter() - start) * 1000)
    success = status is not None and status < 400
    next_retry = None
    if not success and (status is None or status >= 500):
        from datetime import timedelta

        next_retry = datetime.now().replace(tzinfo=None) + timedelta(seconds=_BACKOFF_SECONDS[0])
    log_delivery(
        db,
        merchant_id=hook.merchant_id,
        webhook_id=hook.id,
        event_type=str(body.get("event_type") or "unknown"),
        request_body=body,
        response_status=status,
        response_body=response_text,
        attempt=1,
        success=success,
        error_message=error,
        duration_ms=duration_ms,
        next_retry_at=next_retry,
    )
    if not success:
        logger.warning(
            "merchant webhook delivery failed: url=%s status=%s next_retry_at=%s",
            hook.url,
            status,
            next_retry,
        )
