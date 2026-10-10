"""Admin-edited template copy (subject + intro) with version history.

Only the subject line and the intro paragraph are editable: the layout, legal footer
(CASL sender identification), links and data rows stay in code, so an edit can never
remove the unsubscribe or the sender line. Every save is a new version; the newest
active version wins; "revert" re-saves an older version as the newest.
"""

from __future__ import annotations

import re
import time
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.notification_engine.models import NotificationTemplateCopy

_CACHE: dict[tuple[str, str], dict[str, str]] = {}
_LOADED_AT = 0.0
TTL_SECONDS = 30
#: Placeholders an editor may use; anything else is rejected so a typo can't ship "{oops}".
ALLOWED = frozenset({"merchant", "tracking", "eta_minutes", "window_label", "order_number", "tracking_number", "merchant_name", "stops_line"})
_PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")


def invalidate() -> None:
    global _LOADED_AT
    _LOADED_AT = 0.0


def _load() -> None:
    global _LOADED_AT
    from porterchain_api.db import SessionLocal

    db = SessionLocal()
    try:
        rows = db.query(NotificationTemplateCopy).order_by(NotificationTemplateCopy.version.asc()).all()
        fresh: dict[tuple[str, str], dict[str, str]] = {}
        for row in rows:  # newest version per (template, lang) wins; a cleared version removes the override
            key = (row.template_key, row.lang)
            if row.is_active:
                fresh[key] = {"subject": row.subject or "", "intro": row.intro or "", "version": str(row.version)}
            else:
                fresh.pop(key, None)
        _CACHE.clear()
        _CACHE.update(fresh)
        _LOADED_AT = time.monotonic()
    finally:
        db.close()


def active_copy(template: str, lang: str = "en") -> dict[str, str] | None:
    if time.monotonic() - _LOADED_AT > TTL_SECONDS:
        _load()
    return _CACHE.get((template, lang))


def validate(text: str | None) -> str | None:
    if text is None:
        return None
    clean = " ".join(str(text).split())
    bad = sorted(set(_PLACEHOLDER.findall(clean)) - ALLOWED)
    if bad:
        raise ValueError(f"unknown_placeholder:{','.join(bad)}")
    if clean.count("{") != clean.count("}"):
        raise ValueError("unbalanced_braces")
    return clean or None


def save(db: Session, *, template: str, lang: str, subject: str | None, intro: str | None, author: str | None) -> NotificationTemplateCopy:
    if lang not in ("en", "fr"):
        raise ValueError("lang_invalid")
    subject = validate(subject)
    intro = validate(intro)
    if subject and len(subject) > 200:
        raise ValueError("subject_too_long")
    if intro and len(intro) > 600:
        raise ValueError("intro_too_long")
    last = (
        db.query(NotificationTemplateCopy)
        .filter(NotificationTemplateCopy.template_key == template, NotificationTemplateCopy.lang == lang)
        .order_by(NotificationTemplateCopy.version.desc())
        .first()
    )
    row = NotificationTemplateCopy(
        template_key=template,
        lang=lang,
        version=(last.version + 1) if last else 1,
        subject=subject,
        intro=intro,
        is_active=bool(subject or intro),
        created_by=author,
    )
    db.add(row)
    db.commit()
    invalidate()
    return row


def history(db: Session, template: str) -> list[dict[str, Any]]:
    rows = (
        db.query(NotificationTemplateCopy)
        .filter(NotificationTemplateCopy.template_key == template)
        .order_by(NotificationTemplateCopy.lang.asc(), NotificationTemplateCopy.version.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "lang": r.lang,
            "version": r.version,
            "subject": r.subject,
            "intro": r.intro,
            "active": r.is_active,
            "created_by": r.created_by,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
