"""Transactional email for staff IdP activate / login links."""

from __future__ import annotations

import logging

from porterchain_api.config import Settings
from porterchain_api.notification_engine.delivery_service import DeliveryService

logger = logging.getLogger("porterchain.security")


def activate_url(settings: Settings, token: str) -> str:
    base = (settings.admin_portal_url or "http://localhost:3002").rstrip("/")
    return f"{base}/activate-staff?token={token}"


def security_url(settings: Settings) -> str:
    base = (settings.admin_portal_url or "http://localhost:3002").rstrip("/")
    return f"{base}/account/security"


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


def send_staff_new_login_email(
    settings: Settings,
    *,
    email: str,
    device_label: str,
    client_ip: str,
) -> bool:
    """Notify staff of a sign-in from an unrecognized device/IP."""
    try:
        DeliveryService().deliver(
            {
                "channel": "email",
                "template": "staff_new_login",
                "recipient": email,
                "context": {
                    "email": email,
                    "device_label": device_label or "Unknown device",
                    "client_ip": client_ip or "unknown",
                    "security_url": security_url(settings),
                },
            }
        )
        return True
    except Exception:  # noqa: BLE001
        logger.exception("staff_new_login_email_failed email=%s", email)
        return False


def notify_login_if_new_device(
    settings: Settings,
    *,
    admin_user_id: str,
    email: str,
    client_meta: dict[str, str] | None,
) -> bool:
    """Record + email when this login fingerprint is new vs existing sessions.

    Call **before** minting the new session so existing sessions are the baseline.
    """
    from porterchain_api.auth.sli_metrics import note_auth_event
    from porterchain_api.auth.staff_security_events import (
        is_new_device,
        record_security_event,
    )

    meta = client_meta or {}
    new = is_new_device(admin_user_id, meta)
    record_security_event(
        admin_user_id,
        kind="login",
        detail={
            "client_ip": meta.get("client_ip") or "",
            "device_label": meta.get("device_label") or "",
            "new_device": new,
        },
    )
    if not new:
        note_auth_event("staff_new_device", "known")
        return False
    note_auth_event("staff_new_device", "new")
    record_security_event(
        admin_user_id,
        kind="new_device",
        detail={
            "client_ip": meta.get("client_ip") or "",
            "device_label": meta.get("device_label") or "",
        },
    )
    return send_staff_new_login_email(
        settings,
        email=email,
        device_label=meta.get("device_label") or "",
        client_ip=meta.get("client_ip") or "",
    )
