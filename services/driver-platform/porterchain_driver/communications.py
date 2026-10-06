"""Driver communications — notifications, offline sync, push (Notification Engine)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

NOTIFICATION_GROUPS = (
    "assignment",
    "route_changes",
    "emergency",
    "support",
    "claims",
)

GROUP_TEMPLATES: dict[str, frozenset[str]] = {
    "assignment": frozenset({"driver_assigned", "job_assigned", "driver_accepted", "dispatch.assigned"}),
    "route_changes": frozenset({"driver_route_changed", "tracking_update", "in_transit", "near_delivery"}),
    "emergency": frozenset({"driver_alert", "driver.emergency"}),
    "support": frozenset({"support_ticket_created", "support_reply"}),
    "claims": frozenset({"claim_opened", "claim_updated"}),
}

UPLOAD_ACTION_TYPES = frozenset(
    {"pod_photo", "camera_upload", "pod_signature", "pod_barcode", "document_upload"}
)
GPS_ACTION_TYPES = frozenset({"location"})


class DriverCommunicationService:
    def snapshot(self, db: Session, driver: Any) -> dict[str, Any]:
        from porterchain_driver.offline import OfflineService

        inbox = self.inbox(db, driver.id)
        offline = OfflineService().status(db, driver.id)
        push = self.push_status(db, driver)

        return {
            "push": push,
            "notifications": inbox,
            "offline": offline,
            "realtime": {
                "enabled": True,
                "websocket_path": "/v1/notifications/ws",
            },
            "auto_sync": {"enabled": True, "interval_seconds": 30},
            "last_updated": datetime.now(UTC).isoformat(),
        }

    def inbox(self, db: Session, driver_id: str, *, limit: int = 50, archived: bool = False) -> dict[str, Any]:
        from porterchain_api.notification_engine.models import NotificationRecord

        base = db.query(NotificationRecord).filter(
            NotificationRecord.recipient_type == "driver",
            NotificationRecord.recipient_id == driver_id,
            NotificationRecord.channel == "in_app",
            NotificationRecord.is_archived.is_(archived),
            NotificationRecord.is_sandbox.is_(False),
        )
        rows = base.order_by(NotificationRecord.created_at.desc()).limit(limit).all()
        unread = (
            db.query(NotificationRecord)
            .filter(
                NotificationRecord.recipient_type == "driver",
                NotificationRecord.recipient_id == driver_id,
                NotificationRecord.channel == "in_app",
                NotificationRecord.is_read.is_(False),
                NotificationRecord.is_archived.is_(False),
                NotificationRecord.is_sandbox.is_(False),
            )
            .count()
        )

        items = [self._serialize_notification(r) for r in rows]
        by_group: dict[str, list[dict[str, Any]]] = {g: [] for g in NOTIFICATION_GROUPS}
        for item in items:
            group = self._group_for(item)
            by_group[group].append(item)

        return {
            "unread_count": unread,
            "items": items,
            "by_group": by_group if not archived else {},
        }

    def mark_read(self, db: Session, driver_id: str, notification_id: str) -> bool:
        from porterchain_api.notification_engine.engine import get_notification_engine

        return get_notification_engine().mark_read(
            db, notification_id, user_role="driver", user_id=driver_id
        )

    def mark_archive(self, db: Session, driver_id: str, notification_id: str) -> bool:
        from porterchain_api.notification_engine.engine import get_notification_engine

        return get_notification_engine().mark_archive(
            db, notification_id, user_role="driver", user_id=driver_id
        )

    def mark_all_read(self, db: Session, driver_id: str) -> int:
        from porterchain_api.notification_engine.engine import get_notification_engine

        return get_notification_engine().mark_all_read(db, user_role="driver", user_id=driver_id)

    def push_status(self, db: Session, driver: Any) -> dict[str, Any]:
        from porterchain_api.notification_engine.device_service import DeviceService
        from porterchain_shared.config.settings import get_platform_settings

        devices = DeviceService().list_active(db, user_role="driver", user_id=driver.id)
        settings = get_platform_settings()
        fcm_configured = bool(getattr(settings, "firebase_project_id", None) or getattr(settings, "fcm_server_key", None))
        return {
            "firebase_enabled": True,
            "fcm_configured": fcm_configured,
            "registered_devices": len(devices),
            "devices": [
                {
                    "id": d.id,
                    "platform": d.platform,
                    "device_name": d.device_name,
                    "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
                }
                for d in devices
            ],
        }

    def notify_driver(
        self,
        db: Session,
        driver: Any,
        *,
        title: str,
        body: str,
        template: str = "driver_alert",
        category: str = "orders",
        priority: str = "high",
        deep_link: str | None = None,
        context: dict | None = None,
    ) -> None:
        from porterchain_driver.push import PushService

        PushService().notify_driver(
            db,
            driver,
            title=title,
            body=body,
            template=template,
            data={**(context or {}), "category": category, "priority": priority, "deep_link": deep_link},
        )

    @staticmethod
    def _serialize_notification(record: Any) -> dict[str, Any]:
        ctx = record.context or {}
        return {
            "id": record.id,
            "title": record.title,
            "body": record.body,
            "priority": record.priority,
            "category": record.category,
            "template_key": record.template_key,
            "deep_link": record.deep_link,
            "is_read": record.is_read,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "group": DriverCommunicationService._group_for_template(record.template_key, record.priority),
            "order_id": ctx.get("order_id"),
            "ticket_id": ctx.get("ticket_id"),
            "claim_id": ctx.get("claim_id"),
        }

    @classmethod
    def _group_for(cls, item: dict[str, Any]) -> str:
        return item.get("group") or cls._group_for_template(
            item.get("template_key", ""), item.get("priority", "normal")
        )

    @classmethod
    def _group_for_template(cls, template_key: str, priority: str) -> str:
        if priority == "critical":
            return "emergency"
        for group, templates in GROUP_TEMPLATES.items():
            if template_key in templates:
                return group
        if template_key in GROUP_TEMPLATES["claims"]:
            return "claims"
        return "assignment" if "driver" in template_key else "support"
