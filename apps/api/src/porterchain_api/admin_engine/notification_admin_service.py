"""Admin notification center service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.notification_engine.engine import get_notification_engine
from porterchain_api.notification_engine.models import NotificationDevice, NotificationRecord
from porterchain_api.notification_engine.templates import TEMPLATES, template_meta


class NotificationAdminService:
    def dashboard(self, db: Session) -> dict[str, Any]:
        total = db.query(func.count(NotificationRecord.id)).scalar() or 0
        queued = db.query(func.count(NotificationRecord.id)).filter(NotificationRecord.status == "queued").scalar() or 0
        failed = (
            db.query(func.count(NotificationRecord.id))
            .filter(NotificationRecord.status.in_(["failed", "dead_letter"]))
            .scalar()
            or 0
        )
        devices = db.query(func.count(NotificationDevice.id)).filter(NotificationDevice.is_active.is_(True)).scalar() or 0
        return {
            "total": total,
            "queued": queued,
            "failed": failed,
            "active_devices": devices,
            "templates": len(TEMPLATES),
        }

    def list_records(
        self,
        db: Session,
        *,
        status: str | None = None,
        channel: str | None = None,
        search: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        q = db.query(NotificationRecord)
        if status:
            q = q.filter(NotificationRecord.status == status)
        if channel:
            q = q.filter(NotificationRecord.channel == channel)
        if search:
            like = f"%{search}%"
            q = q.filter(
                or_(
                    NotificationRecord.title.ilike(like),
                    NotificationRecord.recipient_id.ilike(like),
                    NotificationRecord.recipient_address.ilike(like),
                    NotificationRecord.template_key.ilike(like),
                )
            )
        rows = q.order_by(NotificationRecord.created_at.desc()).limit(limit).all()
        return [self._record_dict(r) for r in rows]

    def list_devices(self, db: Session, *, limit: int = 200) -> list[dict[str, Any]]:
        rows = (
            db.query(NotificationDevice)
            .filter(NotificationDevice.is_active.is_(True))
            .order_by(NotificationDevice.last_seen_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": d.id,
                "user_role": d.user_role,
                "user_id": d.user_id,
                "platform": d.platform,
                "device_name": d.device_name,
                "app_version": d.app_version,
                "os_version": d.os_version,
                "language": d.language,
                "timezone": d.timezone,
                "notification_permission": d.notification_permission,
                "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
                "created_at": d.created_at.isoformat(),
            }
            for d in rows
        ]

    def templates_catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "key": key,
                "category": template_meta(key).get("category", "operational"),
                "subject": spec.get("subject", ""),
            }
            for key, spec in TEMPLATES.items()
        ]

    def retry(self, db: Session, notification_id: str) -> bool:
        row = db.get(NotificationRecord, notification_id)
        if not row or row.status not in ("failed", "dead_letter"):
            return False
        row.status = "queued"
        row.next_retry_at = None
        row.failure_reason = None
        db.flush()
        from porterchain_api.booking_engine._core import emit_event
        from porterchain_shared.events.catalog import DomainEventType

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
                "context": {**row.context, "title": row.title, "body": row.body, "deep_link": row.deep_link},
            },
        )
        db.commit()
        return True

    def broadcast(
        self,
        db: Session,
        *,
        recipient_type: str,
        recipient_id: str,
        title: str,
        body: str,
        channel: str = "in_app",
    ) -> dict[str, Any]:
        rec = get_notification_engine().dispatch(
            db,
            event_type="admin.broadcast",
            template_key="system_alert",
            channel=channel,
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            context={"message": body, "title": title, "body": body},
            priority="normal",
        )
        db.commit()
        return {"ok": True, "notification_id": rec.id if rec else None}

    def _record_dict(self, r: NotificationRecord) -> dict[str, Any]:
        return {
            "id": r.id,
            "event_type": r.event_type,
            "template_key": r.template_key,
            "category": r.category,
            "channel": r.channel,
            "priority": r.priority,
            "recipient_type": r.recipient_type,
            "recipient_id": r.recipient_id,
            "recipient_address": r.recipient_address,
            "title": r.title,
            "body": r.body,
            "status": r.status,
            "retry_count": r.retry_count,
            "failure_reason": r.failure_reason,
            "search_tags": r.search_tags,
            "is_read": r.is_read,
            "queued_at": r.queued_at.isoformat() if r.queued_at else None,
            "sent_at": r.sent_at.isoformat() if r.sent_at else None,
            "delivered_at": r.delivered_at.isoformat() if r.delivered_at else None,
            "opened_at": r.opened_at.isoformat() if r.opened_at else None,
            "clicked_at": r.clicked_at.isoformat() if r.clicked_at else None,
            "created_at": r.created_at.isoformat(),
        }
