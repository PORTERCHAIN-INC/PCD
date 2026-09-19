"""Retry due failed merchant webhook deliveries — re-POST without sleep."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import get_settings
from porterchain_api.merchant_engine.secrets import decrypt_signing_secret
from porterchain_api.merchant_engine.webhook_delivery_service import (
    _BACKOFF_SECONDS,
    deliver_webhook_payload,
    log_delivery,
)
from porterchain_api.merchant_models import MerchantWebhook, MerchantWebhookDelivery

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 3


def sweep_merchant_webhook_retries(db: Session, *, limit: int = 25) -> dict[str, Any]:
    """Re-deliver failed webhooks whose next_retry_at is due (no time.sleep)."""
    now = datetime.now(UTC).replace(tzinfo=None)
    rows = (
        db.query(MerchantWebhookDelivery)
        .filter(
            MerchantWebhookDelivery.success.is_(False),
            MerchantWebhookDelivery.next_retry_at.isnot(None),
            MerchantWebhookDelivery.next_retry_at <= now,
            MerchantWebhookDelivery.attempt < _MAX_ATTEMPTS,
        )
        .order_by(MerchantWebhookDelivery.next_retry_at.asc())
        .limit(limit)
        .all()
    )
    retried = 0
    settings = get_settings()
    for row in rows:
        # Clear so concurrent sweepers do not double-fire this row.
        row.next_retry_at = None
        db.flush()

        hook = db.query(MerchantWebhook).filter(MerchantWebhook.id == row.webhook_id).first()
        if not hook or not hook.is_active or not hook.encrypted_signing_secret:
            continue
        try:
            secret = decrypt_signing_secret(
                hook.encrypted_signing_secret, encryption_key=settings.jwt_secret
            )
        except ValueError:
            logger.exception("merchant webhook %s secret decrypt failed on retry", hook.id)
            continue

        body = dict(row.request_body or {})
        attempt = int(row.attempt or 1) + 1
        import time

        start = time.perf_counter()
        status, response_text, error = deliver_webhook_payload(hook.url, body, secret)
        duration_ms = int((time.perf_counter() - start) * 1000)
        success = status is not None and status < 400
        next_retry = None
        if not success and (status is None or status >= 500) and attempt < _MAX_ATTEMPTS:
            delay = _BACKOFF_SECONDS[min(attempt - 1, len(_BACKOFF_SECONDS) - 1)]
            next_retry = datetime.now().replace(tzinfo=None) + timedelta(seconds=delay)
        log_delivery(
            db,
            merchant_id=row.merchant_id,
            webhook_id=row.webhook_id,
            event_type=row.event_type,
            request_body=body,
            response_status=status,
            response_body=response_text,
            attempt=attempt,
            success=success,
            error_message=error,
            duration_ms=duration_ms,
            next_retry_at=next_retry,
        )
        retried += 1
    if rows:
        db.commit()
    return {"due": len(rows), "retried": retried}
