"""Notification Engine — single dispatch entry for all outbound notifications."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from porterchain_shared.events.catalog import DomainEventType
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from porterchain_api.booking_engine._core import emit_event
from porterchain_api.notification_engine.models import NotificationRecord
from porterchain_api.notification_engine.preference_service import PreferenceService
from porterchain_api.notification_engine.realtime import realtime_hub
from porterchain_api.notification_engine.templates import render_email, template_meta

logger = logging.getLogger(__name__)

RETRY_DELAYS_SEC = (30, 120, 480, 1920, 7200)

#: Status for rows parked until quiet hours end (released by the retry sweeper).
HELD = "held"
RECEIVER_TYPES = frozenset({"customer", "consignee"})


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
        exclude_templates: set[str] | None = None,
    ) -> dict:
        """In-app inbox payload for notification center UI."""
        hidden = {"lead_sla_escalation", *(t for t in (exclude_templates or set()) if t)}
        q = db.query(NotificationRecord).filter(
            NotificationRecord.recipient_type == user_role,
            NotificationRecord.recipient_id == user_id,
            NotificationRecord.channel == "in_app",
            NotificationRecord.is_archived.is_(archived),
        )
        if hidden:
            q = q.filter(NotificationRecord.template_key.notin_(hidden))
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
        )
        if hidden:
            unread = unread.filter(NotificationRecord.template_key.notin_(hidden))
        unread = unread.count()

        from porterchain_api.notification_engine.deep_links import (
            group_for,
            href_for,
            label_for,
        )

        return {
            "unread_count": unread,
            "items": [
                {
                    "id": r.id,
                    "href": href_for(r),
                    "group": group_for(r),
                    "entity_label": label_for(r),
                    "template_key": r.template_key,
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
        dedupe_family: str | None = None,
        dedupe_window_sec: int | None = None,
        hold_until: datetime | None = None,
    ) -> NotificationRecord | None:
        """Queue one notification.

        ``dedupe_family`` makes different code paths share one send: a second row in the
        same family (within ``dedupe_window_sec``, or ever when None) is suppressed. It is
        also the per-recipient rate limit (e.g. one ETA email per address per 15 min).
        ``hold_until`` parks the row (status ``held``) instead of sending now.
        """
        ctx = dict(context or {})
        # Receivers (booker/consignee) get the receiver layout in their language;
        # business copies (merchant/driver/admin) stay English and business-styled.
        if recipient_type in RECEIVER_TYPES:
            ctx["audience"] = "receiver"
        else:
            ctx["audience"] = "business"
            for key in ("lang", "reply_to_email", "brand_color", "logo_url"):
                ctx.pop(key, None)
        if recipient_type == "customer" and len(recipient_id) <= 36:
            from porterchain_api.notification_engine.preferences_view import (
                preferred_language,
            )

            pref_lang = preferred_language(db, user_role=recipient_type, user_id=recipient_id)
            if pref_lang:
                ctx["lang"] = pref_lang
        meta = template_meta(template_key)
        cat = category or meta.get("category", "operational")
        if len(recipient_id) > 36:
            from uuid import NAMESPACE_URL, uuid5

            recipient_id = str(uuid5(NAMESPACE_URL, f"{recipient_type}:{recipient_id}"))

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

        from porterchain_api.notification_engine.user_settings import (
            UserSettingsService,
        )

        # Quiet hours hold, never drop: park the row and let the sweeper release it.
        quiet_until = UserSettingsService().hold_until(
            db,
            user_role=recipient_type,
            user_id=recipient_id,
            channel=channel,
            priority=priority,
            category=cat,
        )
        if quiet_until is not None and (hold_until is None or quiet_until > hold_until):
            hold_until = quiet_until

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
            idem_key = idem_key[:255]
            tags["idempotency_key"] = idem_key
            existing = self._find_idempotent(db, idem_key=idem_key)
            if existing:
                return existing

        family = (dedupe_family or "").strip().lower()[:160] or None
        if family and self._family_hit(db, family, window_sec=dedupe_window_sec):
            logger.debug("notification deduped by family %s", family)
            return None

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
            idempotency_key=idem_key,
            dedupe_family=family,
        )
        try:
            with db.begin_nested():
                db.add(record)
                db.flush()
        except IntegrityError:
            # Lost a race on the idempotency key: the other writer's row wins.
            return self._find_idempotent(db, idem_key=idem_key) if idem_key else None

        if hold_until is not None and channel != "in_app" and hold_until > now:
            record.status = HELD
            record.next_retry_at = hold_until
            db.flush()
            logger.debug("notification held until %s: %s/%s", hold_until, recipient_type, channel)
            return record

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
        from porterchain_api.notification_engine.lanes import lane_for

        lane = lane_for(template_key, category=cat, priority=priority)
        record.search_tags = {**(record.search_tags or {}), "lane": lane}
        queue_payload = {
            "notification_id": record.id,
            "lane": lane,
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
    def _find_idempotent(db: Session, *, idem_key: str) -> NotificationRecord | None:
        return (
            db.query(NotificationRecord)
            .filter(NotificationRecord.idempotency_key == idem_key)
            .first()
        )

    @staticmethod
    def _family_hit(db: Session, family: str, *, window_sec: int | None) -> bool:
        q = db.query(NotificationRecord.id).filter(
            NotificationRecord.dedupe_family == family,
            NotificationRecord.status.notin_(("cancelled", "suppressed")),
        )
        if window_sec:
            q = q.filter(NotificationRecord.created_at >= datetime.now(UTC) - timedelta(seconds=int(window_sec)))
        return q.first() is not None

    def dispatch_multi(
        self,
        db: Session,
        specs: list[dict[str, Any]],
        *,
        event_type: str | None = None,
        correlation_id: str | None = None,
    ) -> list[NotificationRecord]:
        """Each spec is isolated in its own savepoint: a bad template or row for one
        recipient never rolls back the others. A failed spec is parked as a dead letter
        (status ``dead_letter``, reason ``dispatch_error:...``) that ops can replay."""
        out: list[NotificationRecord] = []
        for spec in specs:
            try:
                with db.begin_nested():
                    rec = self.dispatch(db, event_type=event_type, correlation_id=correlation_id, **spec)
            except Exception as exc:  # noqa: BLE001 — isolate one recipient's failure
                logger.warning(
                    "notification spec failed (%s/%s/%s): %s",
                    spec.get("template_key"),
                    spec.get("channel"),
                    spec.get("recipient_type"),
                    exc,
                )
                self._dead_letter_spec(db, spec, event_type=event_type, error=exc)
                continue
            if rec:
                out.append(rec)
        return out

    @staticmethod
    def _dead_letter_spec(db: Session, spec: dict[str, Any], *, event_type: str | None, error: Exception) -> None:
        try:
            with db.begin_nested():
                ctx = spec.get("context") or {}
                safe_ctx = {k: (v if isinstance(v, (str, int, float, bool)) or v is None else str(v)) for k, v in ctx.items()}
                db.add(
                    NotificationRecord(
                        event_type=event_type,
                        template_key=str(spec.get("template_key") or "unknown")[:64],
                        category=str(spec.get("category") or "operational")[:32],
                        channel=str(spec.get("channel") or "email")[:16],
                        priority=str(spec.get("priority") or "normal")[:16],
                        recipient_type=str(spec.get("recipient_type") or "unknown")[:32],
                        recipient_id=str(spec.get("recipient_id") or "unknown")[:36],
                        recipient_address=spec.get("recipient_address"),
                        title=str(spec.get("template_key") or "notification")[:255],
                        body="",
                        deep_link=spec.get("deep_link"),
                        status="dead_letter",
                        failure_reason=f"dispatch_error:{type(error).__name__}:{str(error)[:300]}",
                        context=safe_ctx,
                        search_tags=dict(spec.get("search_tags") or {}),
                        queued_at=datetime.now(UTC),
                    )
                )
                db.flush()
        except Exception:
            logger.exception("could not record notification dead letter")

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

    def schedule_retry(self, db: Session, record: NotificationRecord, error: str) -> None:
        record.retry_count += 1
        record.failure_reason = error
        if record.retry_count >= record.max_retries:
            record.status = "dead_letter"
            record.next_retry_at = None
        else:
            from porterchain_api.notification_engine.lanes import jittered

            delay = jittered(RETRY_DELAYS_SEC[min(record.retry_count - 1, len(RETRY_DELAYS_SEC) - 1)])
            record.status = "failed"
            record.next_retry_at = datetime.now(UTC) + timedelta(seconds=delay)
        db.flush()

    def requeue(self, db: Session, notification_id: str) -> bool:
        """Ops retry — re-queue a failed/dead-letter record and emit NOTIFICATION_QUEUED."""
        row = db.get(NotificationRecord, notification_id)
        if not row or row.status not in ("failed", "dead_letter"):
            return False
        was_dispatch_error = (row.failure_reason or "").startswith("dispatch_error:")
        row.next_retry_at = None
        row.failure_reason = None
        if was_dispatch_error:
            # Replay from the stored context: render again (the template may be fixed now).
            title, body, html = render_email(row.template_key, row.context or {})
            row.title, row.body, row.html_body = title[:255], body, html
        if row.channel == "in_app":
            row.status = "sent"
            row.sent_at = datetime.now(UTC)
            db.flush()
            self._broadcast_in_app(row)
            db.commit()
            return True
        row.status = "queued"
        db.flush()
        emit_event(
            db,
            event_type=DomainEventType.NOTIFICATION_QUEUED,
            aggregate_type="notification",
            aggregate_id=row.id,
            payload={
                "notification_id": row.id,
                "lane": (row.search_tags or {}).get("lane"),
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
