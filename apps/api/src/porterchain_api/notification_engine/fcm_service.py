"""FCM delivery — sole Firebase touchpoint in Porterchain."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from porterchain_shared.config.settings import get_platform_settings

logger = logging.getLogger(__name__)

_firebase_app = None

# Android notification channel IDs — must match mobile-driver / web SW expectations.
CHANNEL_OPS_CRITICAL = "ops_critical"
CHANNEL_ASSIGNMENTS = "assignments"
CHANNEL_TRACKING = "tracking"


def resolve_channel_id(*, priority: str = "normal", category: str = "operational") -> str:
    """Map engine priority/category → Android channel_id."""
    pri = (priority or "normal").lower()
    cat = (category or "operational").lower()
    if pri in ("critical", "high") or cat == "security":
        return CHANNEL_OPS_CRITICAL
    if cat == "tracking":
        return CHANNEL_TRACKING
    if cat in ("orders", "claims", "support", "booking"):
        return CHANNEL_ASSIGNMENTS
    return CHANNEL_TRACKING


def _is_urgent(priority: str) -> bool:
    return (priority or "normal").lower() in ("critical", "high")


def _load_credentials(settings: Any) -> dict | None:
    if settings.firebase_credentials_json:
        try:
            return json.loads(settings.firebase_credentials_json)
        except json.JSONDecodeError:
            logger.warning("invalid FIREBASE_CREDENTIALS_JSON")
    path = settings.firebase_credentials_path or ""
    if path and Path(path).is_file():
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return None


def _get_firebase_app():
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app
    settings = get_platform_settings()
    if not settings.firebase_project_id:
        return None
    creds = _load_credentials(settings)
    if not creds:
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            _firebase_app = firebase_admin.initialize_app(credentials.Certificate(creds))
        else:
            _firebase_app = firebase_admin.get_app()
        return _firebase_app
    except ImportError:
        logger.warning("firebase-admin not installed — push log-only")
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("firebase init failed: %s", exc)
        return None


def firebase_sdk_available() -> bool:
    """True when firebase-admin is installed (required for real FCM sends in prod)."""
    try:
        import firebase_admin  # noqa: F401

        return True
    except ImportError:
        return False


def firebase_credentials_configured() -> bool:
    """True when FCM can send real pushes (not log-only)."""
    settings = get_platform_settings()
    if not settings.firebase_project_id:
        return False
    return _load_credentials(settings) is not None


def firebase_production_ready() -> tuple[bool, str | None]:
    """Returns (ready, reason) for health checks and startup validation."""
    settings = get_platform_settings()
    if not settings.push_enabled:
        return True, None
    if settings.app_env in ("local", "development", "test"):
        return True, None
    if not settings.firebase_project_id:
        return False, "FIREBASE_PROJECT_ID not set"
    if not _load_credentials(settings):
        return False, "Firebase credentials missing (FIREBASE_CREDENTIALS_JSON or FIREBASE_CREDENTIALS_PATH)"
    return True, None


def build_fcm_platform_config(
    messaging: Any,
    *,
    priority: str,
    channel_id: str,
) -> tuple[Any, Any]:
    """Return (android_config, apns_config) for OS-level urgency."""
    urgent = _is_urgent(priority)
    android = messaging.AndroidConfig(
        priority="high" if urgent else "normal",
        notification=messaging.AndroidNotification(
            channel_id=channel_id,
            sound="default",
            priority="max" if (priority or "").lower() == "critical" else ("high" if urgent else "default"),
            default_vibrate_timings=urgent,
        ),
    )
    apns_headers = {"apns-priority": "10" if urgent else "5"}
    aps_kwargs: dict[str, Any] = {"sound": "default"}
    if urgent:
        # iOS 15+ time-sensitive (no Critical Alerts entitlement required)
        aps_kwargs["custom_data"] = {"interruption-level": "time-sensitive"}
    apns = messaging.APNSConfig(
        headers=apns_headers,
        payload=messaging.APNSPayload(aps=messaging.Aps(**aps_kwargs)),
    )
    return android, apns


class FCMService:
    INVALID_TOKEN_CODES = {
        "registration-token-not-registered",
        "invalid-argument",
        "invalid-registration-token",
    }

    def send(
        self,
        token: str,
        *,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
        deep_link: str | None = None,
        priority: str = "normal",
        category: str = "operational",
        channel_id: str | None = None,
    ) -> tuple[bool, str | None, bool]:
        """Returns (success, error_message, token_invalid)."""
        settings = get_platform_settings()
        if not settings.push_enabled:
            logger.info("push disabled: token=%s title=%s", token[:16], title)
            return True, None, False
        if not settings.firebase_project_id:
            logger.info("push (log-only): token=%s title=%s", token[:16], title)
            return True, None, False
        if not settings.push_send:
            logger.info("push (dry-run): token=%s title=%s", token[:16], title)
            return True, None, False

        app = _get_firebase_app()
        if not app:
            logger.info("push (no credentials): token=%s title=%s", token[:16], title)
            return True, None, False

        from firebase_admin import messaging

        ch = channel_id or resolve_channel_id(priority=priority, category=category)
        payload_data = {k: str(v) for k, v in (data or {}).items() if v is not None}
        if deep_link:
            payload_data["deep_link"] = deep_link
        payload_data.setdefault("priority", str(priority or "normal"))
        payload_data.setdefault("category", str(category or "operational"))
        payload_data.setdefault("channel_id", ch)

        android, apns = build_fcm_platform_config(messaging, priority=priority, channel_id=ch)

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=payload_data or None,
            token=token,
            android=android,
            apns=apns,
        )
        try:
            messaging.send(message, app=app)
            return True, None, False
        except messaging.UnregisteredError:
            return False, "token_unregistered", True
        except Exception as exc:  # noqa: BLE001
            err = str(exc)
            token_invalid = any(code in err.lower() for code in self.INVALID_TOKEN_CODES)
            return False, err, token_invalid
