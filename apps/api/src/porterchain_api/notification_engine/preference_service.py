"""User notification preferences."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.notification_engine.models import NotificationPreference

DEFAULT_CATEGORIES = (
    "booking",
    "tracking",
    "orders",
    "payments",
    "invoices",
    "claims",
    "support",
    "marketing",
    "security",
)

# Merchant portal event keys → PreferenceService categories (unique mapping).
MERCHANT_EVENT_CATEGORIES: dict[str, tuple[str, ...]] = {
    "order_booked": ("booking",),
    "order_delivered": ("tracking",),
    "order_failed": ("orders",),
    "invoice_generated": ("invoices",),
    "payment_received": ("payments",),
    "claim_updates": ("claims",),
    "support_replies": ("support",),
    "weekly_summary": ("marketing",),
}


def _default_channel_flags(category: str) -> dict[str, bool]:
    """Transactional ON; SMS OFF; marketing OFF."""
    if category == "marketing":
        return {
            "email_enabled": False,
            "push_enabled": False,
            "sms_enabled": False,
            "in_app_enabled": False,
        }
    return {
        "email_enabled": True,
        "push_enabled": True,
        "sms_enabled": False,
        "in_app_enabled": True,
    }


class PreferenceService:
    def is_enabled(
        self,
        db: Session,
        *,
        user_role: str,
        user_id: str,
        category: str,
        channel: str,
    ) -> bool:
        pref = (
            db.query(NotificationPreference)
            .filter(
                NotificationPreference.user_role == user_role,
                NotificationPreference.user_id == user_id,
                NotificationPreference.category == category,
            )
            .first()
        )
        if not pref:
            if category == "marketing":
                return False
            return channel != "sms"
        if channel == "email":
            return pref.email_enabled
        if channel == "push":
            return pref.push_enabled
        if channel == "sms":
            return pref.sms_enabled
        if channel == "in_app":
            return pref.in_app_enabled
        return True

    def get_all(self, db: Session, *, user_role: str, user_id: str) -> list[NotificationPreference]:
        return (
            db.query(NotificationPreference)
            .filter(
                NotificationPreference.user_role == user_role,
                NotificationPreference.user_id == user_id,
            )
            .all()
        )

    def upsert(
        self,
        db: Session,
        *,
        user_role: str,
        user_id: str,
        category: str,
        email_enabled: bool | None = None,
        push_enabled: bool | None = None,
        sms_enabled: bool | None = None,
        in_app_enabled: bool | None = None,
    ) -> NotificationPreference:
        pref = (
            db.query(NotificationPreference)
            .filter(
                NotificationPreference.user_role == user_role,
                NotificationPreference.user_id == user_id,
                NotificationPreference.category == category,
            )
            .first()
        )
        if not pref:
            flags = _default_channel_flags(category)
            pref = NotificationPreference(
                user_role=user_role,
                user_id=user_id,
                category=category,
                **flags,
            )
            db.add(pref)
        if email_enabled is not None:
            pref.email_enabled = email_enabled
        if push_enabled is not None:
            pref.push_enabled = push_enabled
        if sms_enabled is not None:
            pref.sms_enabled = sms_enabled
        if in_app_enabled is not None:
            pref.in_app_enabled = in_app_enabled
        db.flush()
        return pref

    def ensure_defaults(self, db: Session, *, user_role: str, user_id: str) -> None:
        for category in DEFAULT_CATEGORIES:
            existing = (
                db.query(NotificationPreference)
                .filter(
                    NotificationPreference.user_role == user_role,
                    NotificationPreference.user_id == user_id,
                    NotificationPreference.category == category,
                )
                .first()
            )
            if not existing:
                flags = _default_channel_flags(category)
                db.add(
                    NotificationPreference(
                        user_role=user_role,
                        user_id=user_id,
                        category=category,
                        **flags,
                    )
                )
        db.flush()

    def sync_merchant_portal_prefs(
        self,
        db: Session,
        *,
        merchant_id: str,
        portal_prefs: dict[str, Any],
    ) -> None:
        """Bind merchant Settings → NotificationPreference rows (engine SoT)."""
        channels = portal_prefs.get("channels") if isinstance(portal_prefs.get("channels"), dict) else {}
        email_on = bool(channels.get("email", True))
        in_app_on = bool(channels.get("in_app", True))

        for event_key, categories in MERCHANT_EVENT_CATEGORIES.items():
            event_on = bool(portal_prefs.get(event_key, event_key != "weekly_summary"))
            for category in categories:
                self.upsert(
                    db,
                    user_role="merchant",
                    user_id=merchant_id,
                    category=category,
                    email_enabled=email_on and event_on,
                    in_app_enabled=in_app_on and event_on,
                    push_enabled=False,
                    sms_enabled=False,
                )
