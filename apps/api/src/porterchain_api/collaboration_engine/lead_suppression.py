"""Global CRM do-not-contact suppression (hashed email / phone)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.crm_models import CrmSuppression
from porterchain_api.crm_suppression import (
    hash_contact,
    is_suppressed,
    normalize_email,
    normalize_phone,
)

logger = logging.getLogger(__name__)


def upsert_suppression(
    db: Session,
    *,
    email: str | None = None,
    phone: str | None = None,
    source: str,
    lead_id: str | None = None,
) -> list[CrmSuppression]:
    """Insert or refresh suppression rows for email and/or phone."""
    created: list[CrmSuppression] = []
    for kind, normalized in (
        ("email", normalize_email(email)),
        ("phone", normalize_phone(phone)),
    ):
        if not normalized:
            continue
        value_hash = hash_contact(kind, normalized)
        row = (
            db.query(CrmSuppression)
            .filter(CrmSuppression.hash_kind == kind, CrmSuppression.value_hash == value_hash)
            .first()
        )
        if row:
            row.source = source
            if lead_id:
                row.lead_id = lead_id
            created.append(row)
            continue
        row = CrmSuppression(
            hash_kind=kind,
            value_hash=value_hash,
            source=source,
            lead_id=lead_id,
        )
        db.add(row)
        created.append(row)
    if created:
        db.flush()
    return created


def clear_suppression(
    db: Session,
    *,
    email: str | None = None,
    phone: str | None = None,
) -> int:
    """Remove suppression rows (fresh explicit opt-in only)."""
    removed = 0
    for kind, normalized in (
        ("email", normalize_email(email)),
        ("phone", normalize_phone(phone)),
    ):
        if not normalized:
            continue
        value_hash = hash_contact(kind, normalized)
        q = db.query(CrmSuppression).filter(
            CrmSuppression.hash_kind == kind,
            CrmSuppression.value_hash == value_hash,
        )
        removed += q.delete(synchronize_session=False)
    if removed:
        db.flush()
        logger.info("crm_suppression_cleared count=%s", removed)
    return removed


def maybe_clear_on_fresh_opt_in(
    db: Session,
    consent: dict[str, Any] | None,
    *,
    email: str | None,
    phone: str | None,
) -> bool:
    """Clear suppression when consent bag is an explicit fresh marketing opt-in."""
    c = consent or {}
    if c.get("marketing") is not True:
        return False
    if not c.get("captured_at"):
        return False
    # Re-opt-in requires CASL evidence stamp (source + text_version).
    if not c.get("source") or not c.get("text_version"):
        return False
    if c.get("source") == "unsubscribe":
        return False
    cleared = clear_suppression(db, email=email, phone=phone)
    return cleared > 0


def merge_consent_safe(
    existing: dict[str, Any] | None,
    incoming: dict[str, Any] | None,
    *,
    db: Session,
    email: str | None,
    phone: str | None,
) -> dict[str, Any]:
    """Merge consent without resurrecting marketing after unsubscribe / DNC."""
    base = dict(existing or {})
    inc = dict(incoming or {})
    if not inc:
        return base
    if (
        inc.get("method") == "form_checkbox"
        and inc.get("marketing") is False
        and base.get("marketing") is True
    ):
        # An unticked box on a later form is not a withdrawal of earlier consent.
        inc.pop("marketing", None)
        for key in ("text", "text_version", "legal_basis", "captured_at", "source"):
            inc.pop(key, None)

    upgrading = base.get("marketing") is False and inc.get("marketing") is True
    suppressed = is_suppressed(db, email=email, phone=phone)
    if upgrading or (suppressed and inc.get("marketing") is True):
        # Only allow upgrade when incoming is a stamped fresh opt-in that clears DNC.
        if maybe_clear_on_fresh_opt_in(db, inc, email=email, phone=phone):
            base.update(inc)
            return base
        # Keep marketing false; still merge non-marketing keys.
        for key, val in inc.items():
            if key == "marketing":
                continue
            base[key] = val
        base["marketing"] = False
        return base

    base.update(inc)
    # Fresh opt-in on a suppressed contact (marketing already true on lead) still clears.
    if inc.get("marketing") is True:
        maybe_clear_on_fresh_opt_in(db, inc, email=email, phone=phone)
    return base


def apply_consent_for_ingest(
    db: Session,
    consent: dict[str, Any] | None,
    *,
    email: str | None,
    phone: str | None,
) -> dict[str, Any]:
    """Stamp marketing against global DNC for a brand-new lead row."""
    c = dict(consent or {})
    if c.get("marketing") is True and is_suppressed(db, email=email, phone=phone):
        if not maybe_clear_on_fresh_opt_in(db, c, email=email, phone=phone):
            c["marketing"] = False
            return c
        return c
    if c.get("marketing") is True:
        maybe_clear_on_fresh_opt_in(db, c, email=email, phone=phone)
    return c


__all__ = [
    "apply_consent_for_ingest",
    "clear_suppression",
    "hash_contact",
    "is_suppressed",
    "maybe_clear_on_fresh_opt_in",
    "merge_consent_safe",
    "normalize_email",
    "normalize_phone",
    "upsert_suppression",
]
