"""Push notification registration — delegates to Notification Engine DeviceService."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class PushService:
    def register_device(
        self,
        db: Session,
        driver: Any,
        *,
        device_token: str,
        platform: str = "expo",
        device_name: str | None = None,
        app_version: str | None = None,
        os_version: str | None = None,
        language: str = "en-CA",
        timezone: str = "America/Toronto",
        notification_permission: str = "default",
    ) -> dict:
        from porterchain_api.notification_engine.device_service import DeviceService

        svc = DeviceService()
        svc.migrate_legacy_driver_tokens(db, driver)
        device = svc.register(
            db,
            user_role="driver",
            user_id=driver.id,
            fcm_token=device_token,
            platform=platform,
            device_name=device_name,
            app_version=app_version,
            os_version=os_version,
            language=language,
            timezone=timezone,
            notification_permission=notification_permission,
        )
        return {"registered": True, "device_id": device.id, "device_count": len(svc.list_active(db, user_role="driver", user_id=driver.id))}

    def unregister_device(
        self,
        db: Session,
        driver: Any,
        *,
        device_token: str | None = None,
    ) -> dict:
        from porterchain_api.notification_engine.device_service import DeviceService

        svc = DeviceService()
        if device_token:
            svc.invalidate_token(db, device_token)
            return {"unregistered": True, "scope": "token"}
        revoked = svc.revoke_all(db, user_role="driver", user_id=driver.id)
        return {"unregistered": True, "scope": "all", "revoked": revoked}

    def notify_driver(
        self,
        db: Session,
        driver: Any,
        *,
        title: str,
        body: str,
        data: dict | None = None,
        template: str = "driver_alert",
    ) -> None:
        from porterchain_api.notification_engine.engine import get_notification_engine

        get_notification_engine().dispatch(
            db,
            event_type="driver.alert",
            template_key=template,
            channel="push",
            recipient_type="driver",
            recipient_id=driver.id,
            context={"title": title, "body": body, **(data or {})},
            priority="high",
        )
        get_notification_engine().dispatch(
            db,
            event_type="driver.alert",
            template_key=template,
            channel="in_app",
            recipient_type="driver",
            recipient_id=driver.id,
            context={"title": title, "body": body, **(data or {})},
            priority="high",
        )
