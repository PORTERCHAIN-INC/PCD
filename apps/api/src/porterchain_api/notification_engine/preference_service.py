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
    "crm",
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
        priority: str = "normal",
    ) -> bool:
        # Ops risk: staff cannot mute push for high/critical or security.
        if (
            user_role == "admin"
            and channel == "push"
            and (priority in ("critical", "high") or category == "security")
        ):
            return True

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


_TEMPLATE_TOGGLE = {
    "order_created": "order_booked",
    "order_booked": "order_booked",
    "booking_confirmed": "order_booked",
    "parcel_picked_up": "order_delivered",
    "delivered": "order_delivered",
    "order_cancelled": "order_failed",
    "exception_opened": "order_failed",
    "exception_resolved": "order_failed",
    "merchant_invoice_ready": "invoice_generated",
    "payment_receipt": "payment_received",
    "claim_opened": "claim_updates",
    "claim_updated": "claim_updates",
    "support_ticket_created": "support_replies",
    "support_reply": "support_replies",
}


def drop_muted_merchant_specs(db: Session, specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merchant settings toggles bind to the template, not a shared category row."""
    from porterchain_api.merchant_engine.settings_service import DEFAULT_NOTIFICATIONS
    from porterchain_api.merchant_models import Merchant

    cache: dict[str, dict[str, Any]] = {}
    kept: list[dict[str, Any]] = []
    for spec in specs:
        if spec.get("recipient_type") != "merchant":
            kept.append(spec)
            continue
        merchant_id = str(spec.get("recipient_id") or "")
        toggle = _TEMPLATE_TOGGLE.get(str(spec.get("template_key") or ""))
        if not toggle or not merchant_id:
            kept.append(spec)
            continue
        if merchant_id not in cache:
            merchant = db.get(Merchant, merchant_id)
            profile = merchant.profile if merchant and isinstance(merchant.profile, dict) else {}
            settings = profile.get("settings") if isinstance(profile.get("settings"), dict) else {}
            notes = settings.get("notifications") if isinstance(settings.get("notifications"), dict) else {}
            cache[merchant_id] = {**DEFAULT_NOTIFICATIONS, **notes}
        prefs = cache[merchant_id]
        event_on = bool(prefs.get(toggle, toggle != "weekly_summary"))
        channels = prefs.get("channels") if isinstance(prefs.get("channels"), dict) else {}
        channel = str(spec.get("channel") or "")
        channel_on = bool(channels.get(channel, True)) if channel in ("email", "in_app") else True
        if event_on and channel_on:
            kept.append(spec)
    return kept
