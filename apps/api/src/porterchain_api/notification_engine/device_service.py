"""FCM device registration and lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.notification_engine.models import NotificationDevice

MAX_DEVICES_PER_USER = 10


class DeviceService:
    def register(
        self,
        db: Session,
        *,
        user_role: str,
        user_id: str,
        fcm_token: str,
        platform: str,
        device_name: str | None = None,
        app_version: str | None = None,
        os_version: str | None = None,
        language: str = "en-CA",
        timezone: str = "America/Toronto",
        notification_permission: str = "default",
    ) -> NotificationDevice:
        now = datetime.now(UTC)
        existing = (
            db.query(NotificationDevice)
            .filter(
                NotificationDevice.user_role == user_role,
                NotificationDevice.user_id == user_id,
                NotificationDevice.fcm_token == fcm_token,
            )
            .first()
        )
        if existing:
            existing.platform = platform
            existing.device_name = device_name
            existing.app_version = app_version
            existing.os_version = os_version
            existing.language = language
            existing.timezone = timezone
            existing.notification_permission = notification_permission
            existing.is_active = True
            existing.last_seen_at = now
            existing.invalidated_at = None
            db.flush()
            return existing

        device = NotificationDevice(
            user_role=user_role,
            user_id=user_id,
            platform=platform,
            device_name=device_name,
            app_version=app_version,
            os_version=os_version,
            fcm_token=fcm_token,
            language=language,
            timezone=timezone,
            notification_permission=notification_permission,
            is_active=True,
            last_seen_at=now,
        )
        db.add(device)
        db.flush()
        self._trim_devices(db, user_role, user_id)
        return device

    def list_active(self, db: Session, *, user_role: str, user_id: str) -> list[NotificationDevice]:
        return (
            db.query(NotificationDevice)
            .filter(
                NotificationDevice.user_role == user_role,
                NotificationDevice.user_id == user_id,
                NotificationDevice.is_active.is_(True),
            )
            .order_by(NotificationDevice.last_seen_at.desc())
            .all()
        )

    def revoke(self, db: Session, device_id: str, *, user_role: str, user_id: str) -> bool:
        row = (
            db.query(NotificationDevice)
            .filter(
                NotificationDevice.id == device_id,
                NotificationDevice.user_role == user_role,
                NotificationDevice.user_id == user_id,
            )
            .first()
        )
        if not row:
            return False
        row.is_active = False
        row.invalidated_at = datetime.now(UTC)
        db.flush()
        return True

    def revoke_all(self, db: Session, *, user_role: str, user_id: str) -> int:
        rows = (
            db.query(NotificationDevice)
            .filter(NotificationDevice.user_role == user_role, NotificationDevice.user_id == user_id)
            .all()
        )
        now = datetime.now(UTC)
        for row in rows:
            row.is_active = False
            row.invalidated_at = now
        db.flush()
        return len(rows)

    def invalidate_token(self, db: Session, token: str) -> None:
        row = db.query(NotificationDevice).filter(NotificationDevice.fcm_token == token).first()
        if row:
            row.is_active = False
            row.invalidated_at = datetime.now(UTC)
            db.flush()

    def migrate_legacy_driver_tokens(self, db: Session, driver: Any) -> None:
        perf = driver.performance or {}
        for item in perf.get("push_devices") or []:
            token = item.get("token")
            if not token:
                continue
            self.register(
                db,
                user_role="driver",
                user_id=driver.id,
                fcm_token=token,
                platform=item.get("platform") or "expo",
            )

    def _trim_devices(self, db: Session, user_role: str, user_id: str) -> None:
        active = self.list_active(db, user_role=user_role, user_id=user_id)
        if len(active) <= MAX_DEVICES_PER_USER:
            return
        for row in active[MAX_DEVICES_PER_USER:]:
            row.is_active = False
            row.invalidated_at = datetime.now(UTC)
