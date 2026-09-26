"""Global CRM do-not-contact suppression checks (non-engine; safe for intelligence/compliance)."""

from __future__ import annotations

import hashlib
import re

from sqlalchemy.orm import Session

from porterchain_api.crm_models import CrmSuppression

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(value: str | None) -> str | None:
    email = (value or "").strip().lower()
    if not email or not _EMAIL_RE.match(email):
        return None
    return email


def normalize_phone(value: str | None) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None
    digits = re.sub(r"\D+", "", raw)
    if len(digits) < 10:
        return None
    return digits[-11:] if len(digits) >= 11 else digits[-10:]


def hash_contact(kind: str, normalized: str) -> str:
    return hashlib.sha256(f"{kind}:{normalized}".encode("utf-8")).hexdigest()


def is_suppressed(
    db: Session,
    *,
    email: str | None = None,
    phone: str | None = None,
) -> bool:
    email_n = normalize_email(email)
    phone_n = normalize_phone(phone)
    if email_n:
        h = hash_contact("email", email_n)
        if (
            db.query(CrmSuppression.id)
            .filter(CrmSuppression.hash_kind == "email", CrmSuppression.value_hash == h)
            .first()
        ):
            return True
    if phone_n:
        h = hash_contact("phone", phone_n)
        if (
            db.query(CrmSuppression.id)
            .filter(CrmSuppression.hash_kind == "phone", CrmSuppression.value_hash == h)
            .first()
        ):
            return True
    return False


__all__ = [
    "hash_contact",
    "is_suppressed",
    "normalize_email",
    "normalize_phone",
]
