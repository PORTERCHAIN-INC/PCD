"""Quiet hours + user notification settings."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from porterchain_api.notification_engine.models import (
    NotificationDevice,
    NotificationUserSettings,
)

logger = logging.getLogger(__name__)

# Push/SMS muted during quiet hours; email + in_app still deliver (except marketing push already off).
QUIET_MUTED_CHANNELS = frozenset({"push", "sms"})


def _parse_tz(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("America/Toronto")


def is_within_quiet_hours(
    *,
    now: datetime | None = None,
    quiet_start_hour: int,
    quiet_end_hour: int,
    timezone: str,
) -> bool:
    """True when local clock is inside [start, end) wrapping midnight if needed."""
    tz = _parse_tz(timezone or "America/Toronto")
    local = (now or datetime.now(tz)).astimezone(tz)
    hour = local.hour
    start = int(quiet_start_hour) % 24
    end = int(quiet_end_hour) % 24
    if start == end:
        return False
    if start < end:
        return start <= hour < end
    # Wraps midnight (e.g. 22 → 7)
    return hour >= start or hour < end


class UserSettingsService:
    def get(
        self, db: Session, *, user_role: str, user_id: str
    ) -> NotificationUserSettings | None:
        return (
            db.query(NotificationUserSettings)
            .filter(
                NotificationUserSettings.user_role == user_role,
                NotificationUserSettings.user_id == user_id,
            )
            .first()
        )

    def upsert(
        self,
        db: Session,
        *,
        user_role: str,
        user_id: str,
        quiet_hours_enabled: bool | None = None,
        quiet_start_hour: int | None = None,
        quiet_end_hour: int | None = None,
        timezone: str | None = None,
    ) -> NotificationUserSettings:
        row = self.get(db, user_role=user_role, user_id=user_id)
        if not row:
            row = NotificationUserSettings(user_role=user_role, user_id=user_id)
            db.add(row)
        if quiet_hours_enabled is not None:
            row.quiet_hours_enabled = quiet_hours_enabled
        if quiet_start_hour is not None:
            row.quiet_start_hour = max(0, min(23, int(quiet_start_hour)))
        if quiet_end_hour is not None:
            row.quiet_end_hour = max(0, min(23, int(quiet_end_hour)))
        if timezone is not None and timezone.strip():
            row.timezone = timezone.strip()
        db.flush()
        return row

    def resolve_timezone(self, db: Session, *, user_role: str, user_id: str) -> str:
        row = self.get(db, user_role=user_role, user_id=user_id)
        if row and row.timezone:
            return row.timezone
        device = (
            db.query(NotificationDevice)
            .filter(
                NotificationDevice.user_role == user_role,
                NotificationDevice.user_id == user_id,
                NotificationDevice.is_active.is_(True),
            )
            .order_by(NotificationDevice.last_seen_at.desc().nullslast())
            .first()
        )
        if device and device.timezone:
            return device.timezone
        return "America/Toronto"

    def should_mute_channel(
        self,
        db: Session,
        *,
        user_role: str,
        user_id: str,
        channel: str,
        priority: str = "normal",
        category: str = "operational",
    ) -> bool:
        """Mute push/SMS in quiet hours unless critical/security."""
        if channel not in QUIET_MUTED_CHANNELS:
            return False
        if priority in ("critical", "high") or category == "security":
            return False
        row = self.get(db, user_role=user_role, user_id=user_id)
        if not row or not row.quiet_hours_enabled:
            return False
        tz = self.resolve_timezone(db, user_role=user_role, user_id=user_id)
        return is_within_quiet_hours(
            quiet_start_hour=row.quiet_start_hour,
            quiet_end_hour=row.quiet_end_hour,
            timezone=tz,
        )

    def to_dict(self, row: NotificationUserSettings | None, *, timezone_fallback: str) -> dict[str, Any]:
        if not row:
            return {
                "quiet_hours_enabled": False,
                "quiet_start_hour": 22,
                "quiet_end_hour": 7,
                "timezone": timezone_fallback,
            }
        return {
            "quiet_hours_enabled": row.quiet_hours_enabled,
            "quiet_start_hour": row.quiet_start_hour,
            "quiet_end_hour": row.quiet_end_hour,
            "timezone": row.timezone or timezone_fallback,
        }
