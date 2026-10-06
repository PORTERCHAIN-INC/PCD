"""Lead notices stay in Lead Agent unless the watch list is mailed while the admin app is empty."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from porterchain_api.db import SessionLocal
from porterchain_api.notification_engine.models import NotificationDeliveryLog

logger = logging.getLogger(__name__)


def normalize_recipient(payload: dict[str, Any]) -> str:
    raw = payload.get("recipient")
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        return raw.get("email") or raw.get("phone") or raw.get("token") or ""
    return payload.get("email") or payload.get("phone") or ""


def record_internal_inbox_skip(
    notification_id: str | None,
    channel: str,
    template: str,
    recipient: str,
    recipient_type: str,
    context: dict[str, Any],
    mark_deferred: Callable[[str, str], None],
) -> NotificationDeliveryLog:
    logger.info("lead_sla_escalation email suppressed notification_id=%s", notification_id)
    if notification_id:
        mark_deferred(notification_id, "internal_inbox")
    db = SessionLocal()
    try:
        log = NotificationDeliveryLog(
            notification_id=notification_id,
            channel=channel,
            template=template,
            recipient=recipient[:320] if recipient else recipient_type,
            status="skipped",
            error="internal_inbox",
            context=context,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log
    finally:
        db.close()
