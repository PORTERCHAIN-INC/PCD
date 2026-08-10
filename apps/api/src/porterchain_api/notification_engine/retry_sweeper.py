"""Retry due failed notifications — re-enqueue via notification.queued."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_engine._core import emit_event
from porterchain_api.notification_engine.models import NotificationRecord
from porterchain_shared.events.catalog import DomainEventType

logger = logging.getLogger(__name__)


def sweep_notification_retries(db: Session, *, limit: int = 100) -> dict[str, Any]:
    """Re-queue failed notifications whose next_retry_at is due."""
    now = datetime.now(UTC)
    rows = (
        db.query(NotificationRecord)
        .filter(
            NotificationRecord.status == "failed",
            NotificationRecord.next_retry_at.isnot(None),
            NotificationRecord.next_retry_at <= now,
        )
        .order_by(NotificationRecord.next_retry_at.asc())
        .limit(limit)
        .all()
    )
    requeued = 0
    for row in rows:
        if row.retry_count >= row.max_retries:
            row.status = "dead_letter"
            row.next_retry_at = None
            continue
        row.status = "queued"
        row.next_retry_at = None
        emit_event(
            db,
            event_type=DomainEventType.NOTIFICATION_QUEUED,
            aggregate_type="notification",
            aggregate_id=row.id,
            payload={
                "notification_id": row.id,
                "channel": row.channel,
                "template": row.template_key,
                "recipient_type": row.recipient_type,
                "recipient_id": row.recipient_id,
                "recipient": row.recipient_address or "",
                "context": {
                    **(row.context or {}),
                    "title": row.title,
                    "body": row.body,
                    "deep_link": row.deep_link,
                },
            },
        )
        requeued += 1
    if rows:
        db.commit()
    return {"due": len(rows), "requeued": requeued}
