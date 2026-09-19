"""Notification Engine — single dispatch entry for all outbound notifications."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_engine._core import emit_event
from porterchain_api.notification_engine.models import NotificationRecord
from porterchain_api.notification_engine.preference_service import PreferenceService
from porterchain_api.notification_engine.realtime import realtime_hub
from porterchain_api.notification_engine.templates import render_email, template_meta
from porterchain_shared.events.catalog import DomainEventType

logger = logging.getLogger(__name__)

RETRY_DELAYS_SEC = (30, 120, 480, 1920, 7200)


class NotificationEngine:
    def __init__(self) -> None:
        self._prefs = PreferenceService()

    def inbox_payload(
        self,
        db: Session,
        *,
        user_role: str,
        user_id: str,
        unread_only: bool = False,
        archived: bool = False,
        limit: int = 50,
    ) -> dict:
        """In-app inbox payload for notification center UI."""
        q = db.query(NotificationRecord).filter(
            NotificationRecord.recipient_type == user_role,
            NotificationRecord.recipient_id == user_id,
            NotificationRecord.channel == "in_app",
            NotificationRecord.is_archived.is_(archived),
        )
        if unread_only and not archived:
            q = q.filter(NotificationRecord.is_read.is_(False))
        rows = q.order_by(NotificationRecord.created_at.desc()).limit(limit * 2).all()
        # Live inbox default: exclude sandbox-tagged rows.
        filtered = [r for r in rows if not bool(getattr(r, "is_sandbox", False))][:limit]

        unread = (
            db.query(NotificationRecord)
            .filter(
                NotificationRecord.recipient_type == user_role,
                NotificationRecord.recipient_id == user_id,
                NotificationRecord.channel == "in_app",
                NotificationRecord.is_read.is_(False),
                NotificationRecord.is_archived.is_(False),
                NotificationRecord.is_sandbox.is_(False),
            )
            .count()
        )

        return {
            "unread_count": unread,
            "items": [
                {
                    "id": r.id,
                    "title": r.title,
                    "body": r.body,
                    "priority": r.priority,
                    "category": r.category,
                    "deep_link": r.deep_link,
                    "is_read": r.is_read,
                    "is_archived": r.is_archived,
                    "created_at": r.created_at.isoformat(),
                    "is_sandbox": bool(getattr(r, "is_sandbox", False)),
                }
                for r in filtered
            ],
        }

    def dispatch(
        self,
        db: Session,
        *,
        event_type: str | None,
        template_key: str,
        channel: str,
        recipient_type: str,
        recipient_id: str,
        context: dict[str, Any] | None = None,
        recipient_address: str | None = None,
        category: str | None = None,
        priority: str = "normal",
        search_tags: dict[str, Any] | None = None,
        deep_link: str | None = None,
        correlation_id: str | None = None,
    ) -> NotificationRecord | None:
        ctx = dict(context or {})
        meta = template_meta(template_key)
        cat = category or meta.get("category", "operational")

        if not self._prefs.is_enabled(
            db,
            user_role=recipient_type,
            user_id=recipient_id,
            category=cat,
            channel=channel,
            priority=priority,
        ):
            logger.debug("notification suppressed by preference: %s/%s/%s", recipient_type, cat, channel)
            return None

        from porterchain_api.notification_engine.user_settings import UserSettingsService

        if UserSettingsService().should_mute_channel(
            db,
            user_role=recipient_type,
            user_id=recipient_id,
            channel=channel,
            priority=priority,
            category=cat,
        ):
            logger.debug(
                "notification muted by quiet hours: %s/%s/%s",
                recipient_type,
                channel,
                cat,
            )
            return None

        # Do not queue doomed FCM rows — no active device means push_token_required forever.
        # Admin high/critical still queues so DeliveryService can email-fallback.
        if channel == "push" and not (
            recipient_type == "admin" and priority in ("critical", "high")
        ):
            from porterchain_api.notification_engine.device_service import DeviceService

            if not DeviceService().list_active(db, user_role=recipient_type, user_id=recipient_id):
                logger.debug(
                    "push suppressed: no active device for %s/%s",
                    recipient_type,
                    recipient_id,
                )
                return None

        tags = dict(search_tags or {})
        idem_key: str | None = None
        if event_type and correlation_id:
            idem_key = (
                f"{event_type}|{correlation_id}|{template_key}|{channel}|{recipient_type}|{recipient_id}"
            )
            tags["idempotency_key"] = idem_key
            existing = self._find_idempotent(db, event_type=event_type, template_key=template_key, channel=channel, recipient_type=recipient_type, recipient_id=recipient_id, idem_key=idem_key)
            if existing:
                return existing

        title, body, html = render_email(template_key, ctx)
        now = datetime.now(UTC)
        is_sandbox = bool(ctx.get("is_sandbox") is True or tags.get("is_sandbox") is True)
        if is_sandbox:
            tags["is_sandbox"] = True
            ctx = {**ctx, "is_sandbox": True}

        record = NotificationRecord(
            event_type=event_type,
            template_key=template_key,
            category=cat,
            channel=channel,
            priority=priority,
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            recipient_address=recipient_address,
            title=title,
            body=body,
            html_body=html,
            deep_link=deep_link or ctx.get("deep_link"),
            status="queued",
            context=ctx,
            search_tags=tags,
            is_sandbox=is_sandbox,
            queued_at=now,
        )
        db.add(record)
        db.flush()

        if channel == "in_app":
            record.status = "sent"
            record.sent_at = now
            db.flush()
            self._broadcast_in_app(record)
            # Audit only — do not publish to the bus (no subscribers; flooded lag).
            emit_event(
                db,
                event_type=DomainEventType.NOTIFICATION_SENT,
                aggregate_type="notification",
                aggregate_id=record.id,
                correlation_id=correlation_id,
                payload={"channel": channel, "template": template_key, "notification_id": record.id},
                publish=False,
            )
            return record

        # Worker-only delivery for email/SMS/push (auth-critical mail uses staff_mail sync path).
        # priority/category must ride the queue so FCM can set OS urgency.
        queue_payload = {
            "notification_id": record.id,
            "channel": channel,
            "template": template_key,
            "recipient_type": recipient_type,
            "recipient_id": recipient_id,
            "recipient": recipient_address or "",
            "context": {
                **ctx,
                "title": title,
                "body": body,
                "deep_link": record.deep_link,
                "priority": priority,
                "category": cat,
            },
        }
        emit_event(
            db,
            event_type=DomainEventType.NOTIFICATION_QUEUED,
            aggregate_type="notification",
            aggregate_id=record.id,
            correlation_id=correlation_id or record.id,
            payload=queue_payload,
        )
        return record

    @staticmethod
    def _find_idempotent(
        db: Session,
        *,
        event_type: str,
        template_key: str,
        channel: str,
        recipient_type: str,
        recipient_id: str,
        idem_key: str,
    ) -> NotificationRecord | None:
        try:
            hit = (
                db.query(NotificationRecord)
                .filter(
                    NotificationRecord.event_type == event_type,
                    NotificationRecord.template_key == template_key,
                    NotificationRecord.channel == channel,
                    NotificationRecord.recipient_type == recipient_type,
                    NotificationRecord.recipient_id == recipient_id,
                    NotificationRecord.search_tags["idempotency_key"].as_string() == idem_key,
                )
                .order_by(NotificationRecord.created_at.desc())
                .first()
            )
            if hit:
                return hit
        except Exception:  # noqa: BLE001 — JSON path may be unavailable in some dialects
            pass
        candidates = (
            db.query(NotificationRecord)
            .filter(
                NotificationRecord.event_type == event_type,
                NotificationRecord.template_key == template_key,
                NotificationRecord.channel == channel,
                NotificationRecord.recipient_type == recipient_type,
                NotificationRecord.recipient_id == recipient_id,
            )
            .order_by(NotificationRecord.created_at.desc())
            .limit(100)
            .all()
        )
        for row in candidates:
            if (row.search_tags or {}).get("idempotency_key") == idem_key:
                return row
        return None

    def dispatch_multi(
        self,
        db: Session,
        specs: list[dict[str, Any]],
        *,
        event_type: str | None = None,
        correlation_id: str | None = None,
    ) -> list[NotificationRecord]:
        out: list[NotificationRecord] = []
        for spec in specs:
            rec = self.dispatch(db, event_type=event_type, correlation_id=correlation_id, **spec)
            if rec:
                out.append(rec)
        return out

    def mark_read(self, db: Session, notification_id: str, *, user_role: str, user_id: str) -> bool:
        row = (
            db.query(NotificationRecord)
            .filter(
                NotificationRecord.id == notification_id,
                NotificationRecord.recipient_type == user_role,
                NotificationRecord.recipient_id == user_id,
            )
            .first()
        )
        if not row:
            return False
        row.is_read = True
        if not row.opened_at:
            row.opened_at = datetime.now(UTC)
        db.flush()
        return True

    def mark_archive(self, db: Session, notification_id: str, *, user_role: str, user_id: str) -> bool:
        row = (
            db.query(NotificationRecord)
            .filter(
                NotificationRecord.id == notification_id,
                NotificationRecord.recipient_type == user_role,
                NotificationRecord.recipient_id == user_id,
            )
            .first()
        )
        if not row:
            return False
        row.is_archived = True
        row.is_read = True
        db.flush()
        return True

    def mark_all_read(self, db: Session, *, user_role: str, user_id: str) -> int:
        rows = (
            db.query(NotificationRecord)
            .filter(
                NotificationRecord.recipient_type == user_role,
                NotificationRecord.recipient_id == user_id,
                NotificationRecord.channel == "in_app",
                NotificationRecord.is_archived.is_(False),
                NotificationRecord.is_read.is_(False),
            )
            .all()
        )
        now = datetime.now(UTC)
        for row in rows:
            row.is_read = True
            if not row.opened_at:
                row.opened_at = now
        db.flush()
        return len(rows)

    def mark_clicked(self, db: Session, notification_id: str, *, user_role: str, user_id: str) -> bool:
        row = (
            db.query(NotificationRecord)
            .filter(
                NotificationRecord.id == notification_id,
                NotificationRecord.recipient_type == user_role,
                NotificationRecord.recipient_id == user_id,
            )
            .first()
        )
        if not row:
            return False
        row.clicked_at = datetime.now(UTC)
        row.is_read = True
        db.flush()
        return True

    def schedule_retry(self, db: Session, record: NotificationRecord, error: str) -> None:
        record.retry_count += 1
        record.failure_reason = error
        if record.retry_count >= record.max_retries:
            record.status = "dead_letter"
            record.next_retry_at = None
        else:
            delay = RETRY_DELAYS_SEC[min(record.retry_count - 1, len(RETRY_DELAYS_SEC) - 1)]
            record.status = "failed"
            record.next_retry_at = datetime.now(UTC) + timedelta(seconds=delay)
        db.flush()

    def requeue(self, db: Session, notification_id: str) -> bool:
        """Ops retry — re-queue a failed/dead-letter record and emit NOTIFICATION_QUEUED."""
        row = db.get(NotificationRecord, notification_id)
        if not row or row.status not in ("failed", "dead_letter"):
            return False
        row.status = "queued"
        row.next_retry_at = None
        row.failure_reason = None
        db.flush()
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
                    **row.context,
                    "title": row.title,
                    "body": row.body,
                    "deep_link": row.deep_link,
                },
            },
        )
        db.commit()
        return True

    def _broadcast_in_app(self, record: NotificationRecord) -> None:
        realtime_hub.broadcast_sync(
            record.recipient_type,
            record.recipient_id,
            {
                "type": "notification",
                "data": {
                    "id": record.id,
                    "title": record.title,
                    "body": record.body,
                    "priority": record.priority,
                    "category": record.category,
                    "deep_link": record.deep_link,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                    "is_read": record.is_read,
                },
            },
        )


_engine: NotificationEngine | None = None


def get_notification_engine() -> NotificationEngine:
    global _engine
    if _engine is None:
        _engine = NotificationEngine()
    return _engine
