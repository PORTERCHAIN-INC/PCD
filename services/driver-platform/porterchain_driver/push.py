"""Push notification registration for drivers."""

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
    ) -> dict:
        perf = dict(driver.performance or {})
        devices = list(perf.get("push_devices", []))
        devices = [d for d in devices if d.get("token") != device_token]
        devices.append({"token": device_token, "platform": platform})
        perf["push_devices"] = devices[-5:]
        driver.performance = perf
        db.flush()
        return {"registered": True, "device_count": len(devices)}

    def notify_driver(
        self,
        db: Session,
        driver: Any,
        *,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> None:
        from porterchain_api.booking_engine._core import emit_event
        from porterchain_shared.events.catalog import DomainEventType

        emit_event(
            db,
            event_type=DomainEventType.NOTIFICATION_QUEUED,
            aggregate_type="driver",
            aggregate_id=driver.id,
            actor_type="system",
            payload={
                "channel": "push",
                "template": "driver_alert",
                "recipient": {"driver_id": driver.id, "devices": (driver.performance or {}).get("push_devices", [])},
                "context": {"title": title, "body": body, **(data or {})},
            },
        )
