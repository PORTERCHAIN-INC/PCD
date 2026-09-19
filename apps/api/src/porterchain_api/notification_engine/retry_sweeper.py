"""Retry due failed notifications — re-enqueue via notification.queued."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_engine._core import emit_event
from porterchain_api.notification_engine.models import NotificationRecord
from porterchain_shared.events.catalog import DomainEventType

logger = logging.getLogger(__name__)

# Email/SMS/push stuck in queued means notification.queued never drained (stream lag).
STALE_QUEUED_SECONDS = 120


def _requeue_payload(row: NotificationRecord) -> dict[str, Any]:
    return {
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
            "priority": row.priority or "normal",
            "category": row.category or "operational",
        },
    }


def _emit_queued(db: Session, row: NotificationRecord) -> None:
    emit_event(
        db,
        event_type=DomainEventType.NOTIFICATION_QUEUED,
        aggregate_type="notification",
        aggregate_id=row.id,
        payload=_requeue_payload(row),
    )


def sweep_notification_retries(db: Session, *, limit: int = 100) -> dict[str, Any]:
    """Re-queue failed-due + stale queued email/SMS/push; drop doomed no-device push."""
    now = datetime.now(UTC)
    failed_rows = (
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
    for row in failed_rows:
        if row.retry_count >= row.max_retries:
            row.status = "dead_letter"
            row.next_retry_at = None
            continue
        row.status = "queued"
        row.next_retry_at = None
        _emit_queued(db, row)
        requeued += 1

    # Cancel queued push with no FCM device — retries only burn the stream.
    from porterchain_api.notification_engine.device_service import DeviceService

    devices = DeviceService()
    doomed_budget = max(0, limit - len(failed_rows))
    doomed_push = (
        db.query(NotificationRecord)
        .filter(
            NotificationRecord.status == "queued",
            NotificationRecord.channel == "push",
        )
        .order_by(NotificationRecord.queued_at.asc().nullsfirst())
        .limit(doomed_budget)
        .all()
        if doomed_budget
        else []
    )
    cancelled_no_device = 0
    for row in doomed_push:
        if row.recipient_type == "admin" and (row.priority or "normal") in ("critical", "high"):
            continue
        if devices.list_active(db, user_role=row.recipient_type, user_id=row.recipient_id):
            continue
        row.status = "deferred"
        row.failure_reason = "push_token_required"
        row.next_retry_at = None
        cancelled_no_device += 1

    stale_cutoff = now - timedelta(seconds=STALE_QUEUED_SECONDS)
    stale_budget = max(0, limit - len(failed_rows))
    stale_rows = (
        db.query(NotificationRecord)
        .filter(
            NotificationRecord.status == "queued",
            NotificationRecord.channel.in_(("email", "sms", "push")),
            NotificationRecord.queued_at.isnot(None),
            NotificationRecord.queued_at <= stale_cutoff,
        )
        .order_by(NotificationRecord.queued_at.asc())
        .limit(stale_budget)
        .all()
        if stale_budget
        else []
    )
    stale_requeued = 0
    for row in stale_rows:
        row.queued_at = now
        _emit_queued(db, row)
        stale_requeued += 1

    if failed_rows or doomed_push or stale_rows:
        db.commit()
    return {
        "due": len(failed_rows),
        "requeued": requeued,
        "stale_queued": len(stale_rows),
        "stale_requeued": stale_requeued,
        "push_no_device_deferred": cancelled_no_device,
    }
