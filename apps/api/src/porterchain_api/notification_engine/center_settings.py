"""Notification center switches: per-event x persona matrix and the ops digest flags."""

from __future__ import annotations

import copy
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.notification_engine.models import NotificationAdminSetting

MATRIX_KEY = "matrix_off"
DIGEST_KEY = "ops_digest"
DIGEST_DEFAULT: dict[str, Any] = {"enabled": False, "approved": False, "approved_by": None, "approved_at": None, "last_sent_date": None, "send_hour": 7}

#: Personas shown in the matrix. "receiver" = recipient-experience emails (cx.*).
PERSONAS = ("receiver", "customer", "merchant", "driver", "admin")
#: Rows nobody may switch off: security and money.
LOCKED_TEMPLATES = frozenset({"password_reset", "otp", "staff_activate", "staff_new_login", "payment_receipt", "payment_failed"})


def get_setting(db: Session, key: str, default: Any) -> Any:
    row = db.get(NotificationAdminSetting, key)
    if row is None or row.value is None:
        return copy.deepcopy(default)
    if isinstance(default, dict) and isinstance(row.value, dict):
        return {**copy.deepcopy(default), **row.value}
    return row.value


def set_setting(db: Session, key: str, value: Any, *, author: str | None) -> None:
    row = db.get(NotificationAdminSetting, key)
    if row is None:
        db.add(NotificationAdminSetting(key=key, value=value, updated_by=author))
    else:
        row.value = value
        row.updated_by = author
    db.commit()


def matrix_off(db: Session) -> set[str]:
    raw = get_setting(db, MATRIX_KEY, {"off": []})
    off = raw.get("off") if isinstance(raw, dict) else []
    return {str(x) for x in off or []}


def set_matrix_cell(db: Session, event: str, persona: str, enabled: bool, *, author: str | None) -> set[str]:
    if persona not in PERSONAS:
        raise ValueError("persona_invalid")
    off = matrix_off(db)
    key = f"{event}|{persona}"
    if enabled:
        off.discard(key)
    else:
        off.add(key)
    set_setting(db, MATRIX_KEY, {"off": sorted(off)}, author=author)
    return off


def drop_matrix_off(db: Session, event_type: str, specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    off = matrix_off(db)
    if not off:
        return specs
    kept = []
    for spec in specs:
        persona = "receiver" if spec.get("recipient_type") == "consignee" else str(spec.get("recipient_type"))
        if f"{event_type}|{persona}" in off and spec.get("template_key") not in LOCKED_TEMPLATES:
            continue
        kept.append(spec)
    return kept


def cx_kind_enabled(db: Session, kind: str) -> bool:
    return f"cx.{kind}|receiver" not in matrix_off(db)
