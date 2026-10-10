"""Alert the owner/super admins on repeated failed staff sign-ins (one email per IP per hour).

Internal security email only (to active super admins + SECURITY_ALERT_EMAIL); never to
customers or merchants.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

THRESHOLD = 5          # failures per IP inside the window
WINDOW_SECONDS = 15 * 60
COOLDOWN_SECONDS = 60 * 60


def _redis():
    from porterchain_api.auth.staff_security_events import _client

    return _client()


def recipients(db: Any, settings: Any) -> list[str]:
    from porterchain_api.admin_models import AdminUser

    out = {e.strip().lower() for e in str(getattr(settings, "security_alert_email", "") or "").split(",") if e.strip()}
    try:
        rows = db.query(AdminUser).filter(AdminUser.role == "super_admin", AdminUser.is_active.is_(True)).all()
        out |= {r.email.strip().lower() for r in rows if r.email}
    except Exception:  # noqa: BLE001
        logger.exception("staff_login_alert_recipients_failed")
    return sorted(out)


def note_failed_login(db: Any, settings: Any, *, client_ip: str, factor: str, send=None) -> bool:
    """Count a failure; at THRESHOLD send one alert per IP per cooldown. Returns True if alerted."""
    client = _redis()
    if client is None:
        logger.warning("staff_login_failed ip=%s factor=%s (redis down, no counter)", client_ip, factor)
        return False
    key = f"staff_login_fail:{client_ip}"
    count = int(client.incr(key))
    if count == 1:
        client.expire(key, WINDOW_SECONDS)
    logger.warning("staff_login_failed ip=%s factor=%s count=%s", client_ip, factor, count)
    if count < THRESHOLD or not client.set(f"staff_login_alerted:{client_ip}", "1", nx=True, ex=COOLDOWN_SECONDS):
        return False
    message = (
        f"{count} failed PorterChain Admin sign-in attempts in the last {WINDOW_SECONDS // 60} minutes "
        f"from IP {client_ip} (factor: {factor}). Sign-in is rate limited. If this was not you or "
        "your team, review Admin > Security and consider enabling the admin IP allowlist."
    )
    deliver = send or _send
    for to in recipients(db, settings):
        deliver(to, message)
    return True


def _send(to: str, message: str) -> None:
    try:
        from porterchain_api.notification_engine.delivery_service import DeliveryService

        DeliveryService().deliver({"channel": "email", "template": "system_alert", "recipient": to,
                                   "context": {"message": message, "subject": "Failed Admin sign-ins"}})
    except Exception:  # noqa: BLE001
        logger.exception("staff_login_alert_send_failed")
