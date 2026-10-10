"""One preferences model per persona: category x (email, in-app), quiet hours, language.

CASL: transactional / service email (booking, delivery updates, receipts, invoices,
claims, support replies, security) is exempt from consent and stays ON: those toggles
are locked. Marketing / product news needs express consent: off by default, and turning
it on records when and where consent was given. Unsubscribing turns it off.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.notification_engine.preference_service import EMAIL_LOCKED as _EMAIL_LOCKED
from porterchain_api.notification_engine.preference_service import PreferenceService
from porterchain_api.notification_engine.user_settings import UserSettingsService

LABELS: dict[str, tuple[str, str]] = {
    "booking": ("Bookings", "Confirmations and changes to your bookings"),
    "tracking": ("Delivery updates", "Out for delivery, ETA, delivered, missed attempts"),
    "orders": ("Orders & jobs", "New, failed and rescheduled orders"),
    "payments": ("Payments", "Receipts, failed payments, payouts"),
    "invoices": ("Invoices", "New invoices and reminders"),
    "claims": ("Claims", "Damage and loss claim updates"),
    "support": ("Support", "Replies from our team"),
    "crm": ("Leads", "New leads, SLA warnings and assignments"),
    "security": ("Security", "Sign-in codes and new sign-ins"),
    "marketing": ("News & offers", "Product news and occasional offers"),
}
PERSONA_CATEGORIES: dict[str, tuple[str, ...]] = {
    "customer": ("tracking", "booking", "payments", "invoices", "claims", "support", "security", "marketing"),
    "merchant": ("orders", "tracking", "booking", "invoices", "payments", "claims", "support", "security", "marketing"),
    "driver": ("orders", "payments", "support", "security"),
    "admin": ("orders", "crm", "claims", "support", "payments", "security"),
}
#: Email that CASL treats as transactional and we never let anyone switch off.
EMAIL_LOCKED = _EMAIL_LOCKED
#: The bell can be quieted for anything except security.
IN_APP_LOCKED = frozenset({"security"})
CONSENT_CATEGORIES = frozenset({"marketing"})
LANGUAGE_PERSONAS = frozenset({"customer"})


def persona_of(user_role: str) -> str:
    return "customer" if user_role in ("customer", "consignee") else user_role


def view(db: Session, *, user_role: str, user_id: str) -> dict[str, Any]:
    persona = persona_of(user_role)
    prefs = PreferenceService()
    prefs.ensure_defaults(db, user_role=user_role, user_id=user_id)
    rows = {p.category: p for p in prefs.get_all(db, user_role=user_role, user_id=user_id)}
    us = UserSettingsService()
    row = us.get(db, user_role=user_role, user_id=user_id)
    base = us.to_dict(row, timezone_fallback=us.resolve_timezone(db, user_role=user_role, user_id=user_id))
    cats = []
    for cat in PERSONA_CATEGORIES.get(persona, PERSONA_CATEGORIES["customer"]):
        p = rows.get(cat)
        label, hint = LABELS[cat]
        cats.append(
            {
                "key": cat,
                "label": label,
                "hint": hint,
                "email": True if cat in EMAIL_LOCKED else bool(p and p.email_enabled),
                "in_app": True if cat in IN_APP_LOCKED else bool(p.in_app_enabled if p else cat != "marketing"),
                "email_locked": cat in EMAIL_LOCKED,
                "in_app_locked": cat in IN_APP_LOCKED,
                "needs_consent": cat in CONSENT_CATEGORIES,
            }
        )
    return {
        "persona": persona,
        "categories": cats,
        "quiet_hours": {
            "enabled": base["quiet_hours_enabled"],
            "start": base["quiet_start_hour"],
            "end": base["quiet_end_hour"],
            "timezone": base["timezone"],
        },
        "language": (row.language if row and row.language else "auto") if persona in LANGUAGE_PERSONAS else None,
        "marketing_consent_at": row.marketing_consent_at.isoformat() if row and row.marketing_consent_at else None,
    }


def update(db: Session, *, user_role: str, user_id: str, body: dict[str, Any]) -> dict[str, Any]:
    persona = persona_of(user_role)
    allowed = set(PERSONA_CATEGORIES.get(persona, ()))
    prefs = PreferenceService()
    us = UserSettingsService()
    for cat, flags in (body.get("categories") or {}).items():
        if cat not in allowed or not isinstance(flags, dict):
            raise ValueError(f"category_invalid:{cat}")
        email = flags.get("email")
        in_app = flags.get("in_app")
        if email is False and cat in EMAIL_LOCKED:
            raise ValueError(f"email_locked:{cat}")
        if in_app is False and cat in IN_APP_LOCKED:
            raise ValueError(f"in_app_locked:{cat}")
        prefs.upsert(
            db,
            user_role=user_role,
            user_id=user_id,
            category=cat,
            email_enabled=None if email is None else bool(email),
            in_app_enabled=None if in_app is None else bool(in_app),
        )
        if cat in CONSENT_CATEGORIES and email is not None:
            row = us.upsert(db, user_role=user_role, user_id=user_id)
            if email:
                row.marketing_consent_at = datetime.now(UTC)
                row.marketing_consent_source = f"{persona}_preferences"
            else:
                row.marketing_consent_at = None
                row.marketing_consent_source = None
    qh = body.get("quiet_hours")
    if isinstance(qh, dict):
        us.upsert(
            db,
            user_role=user_role,
            user_id=user_id,
            quiet_hours_enabled=qh.get("enabled"),
            quiet_start_hour=qh.get("start"),
            quiet_end_hour=qh.get("end"),
            timezone=qh.get("timezone"),
        )
    if "language" in body and persona in LANGUAGE_PERSONAS:
        lang = body.get("language") or "auto"
        if lang not in ("auto", "en", "fr"):
            raise ValueError("language_invalid")
        row = us.upsert(db, user_role=user_role, user_id=user_id)
        row.language = None if lang == "auto" else lang
    db.flush()
    return view(db, user_role=user_role, user_id=user_id)


def preferred_language(db: Session, *, user_role: str, user_id: str) -> str | None:
    if persona_of(user_role) not in LANGUAGE_PERSONAS:
        return None
    row = UserSettingsService().get(db, user_role=user_role, user_id=user_id)
    return row.language if row and row.language else None
