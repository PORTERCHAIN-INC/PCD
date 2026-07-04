"""User notification preferences."""

from __future__ import annotations

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
            pref = NotificationPreference(user_role=user_role, user_id=user_id, category=category)
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
                db.add(NotificationPreference(user_role=user_role, user_id=user_id, category=category))
        db.flush()
