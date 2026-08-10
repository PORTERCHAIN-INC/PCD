"""Transactional email for staff IdP activate / login links."""

from __future__ import annotations

import logging

from porterchain_api.config import Settings
from porterchain_api.notification_engine.delivery_service import DeliveryService

logger = logging.getLogger("porterchain.security")


def activate_url(settings: Settings, token: str) -> str:
    base = (settings.admin_portal_url or "http://localhost:3002").rstrip("/")
    return f"{base}/activate-staff?token={token}"


def send_staff_activate_email(settings: Settings, *, email: str, token: str) -> bool:
    """Send activate link. Returns True if delivery attempted without raising."""
    url = activate_url(settings, token)
    try:
        DeliveryService().deliver(
            {
                "channel": "email",
                "template": "staff_activate",
                "recipient": email,
                "context": {"activate_url": url, "email": email},
            }
        )
        return True
    except Exception:  # noqa: BLE001 — auth flow must not fail on SMTP blips
        logger.exception("staff_activate_email_failed email=%s", email)
        return False
