"""Exactly-once send claim: one worker owns a notification row while it sends.

The queue is at-least-once (duplicate events, retries, redelivery after a crash), so
the row is the lock. ``claim`` atomically flips a sendable row to ``sending``; a second
worker holding the same message sees rowcount 0 and skips. A crash mid-send leaves a
``sending`` row that becomes claimable again after STALE_AFTER.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, or_, update

from porterchain_api.db import SessionLocal
from porterchain_api.notification_engine.models import NotificationRecord

SENDING = "sending"
STALE_AFTER = timedelta(minutes=10)
DONE = ("sent", "delivered", "bounced", "cancelled", "suppressed", "held")


def claim(notification_id: str) -> tuple[bool, str | None]:
    """Return (claimed, previous_status). Unknown rows (legacy payloads) are allowed."""
    db = SessionLocal()
    try:
        row = db.get(NotificationRecord, notification_id)
        if row is None:
            return True, None
        previous = row.status
        stale = datetime.now(UTC) - STALE_AFTER
        res = db.execute(
            update(NotificationRecord)
            .where(
                NotificationRecord.id == notification_id,
                or_(
                    NotificationRecord.status.notin_((*DONE, SENDING)),
                    and_(NotificationRecord.status == SENDING, NotificationRecord.updated_at < stale),
                ),
            )
            .values(status=SENDING, updated_at=datetime.now(UTC))
            .execution_options(synchronize_session=False)
        )
        db.commit()
        return res.rowcount == 1, previous
    finally:
        db.close()


def release(notification_id: str, previous: str | None) -> None:
    """If the send path finished without setting an outcome, put the old status back."""
    db = SessionLocal()
    try:
        db.execute(
            update(NotificationRecord)
            .where(NotificationRecord.id == notification_id, NotificationRecord.status == SENDING)
            .values(status=previous or "queued")
            .execution_options(synchronize_session=False)
        )
        db.commit()
    finally:
        db.close()
