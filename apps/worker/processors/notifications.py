"""Notification delivery — delegates to notification_engine."""

from __future__ import annotations

from typing import Any

from porterchain_api.notification_engine import deliver_notification


def process_notification(payload: dict[str, Any]) -> None:
    deliver_notification(payload)
