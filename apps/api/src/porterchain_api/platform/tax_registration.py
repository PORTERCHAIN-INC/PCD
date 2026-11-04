"""PorterChain's GST/HST registration — the single source of truth for charging tax.

Every tax computation and every tax line on a document asks this module first:

* ``collects_tax(db, at)`` — are we a GST/HST registrant on that date? If not, we are a
  non-registrant (small supplier, ETA s.148) and must not charge, collect or show GST/HST
  (ETA s.221 / s.225; see docs/compliance/INVOICE_ADJUSTMENTS_CANADA.md §10).
* ``supplier_gst_hst_number(db, at)`` — the number to print, or ``''``.

History lives in ``tax_registrations`` (append-only). The registration in force on a day
is the latest row with ``effective_from`` on or before that day (America/Toronto). A row
with no number means "not registered from that day". Issued invoices keep the tax they
were issued with; nothing here rewrites them.

CRA number format: 9-digit Business Number + ``RT`` + 4-digit reference
(e.g. ``123456789 RT0001``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo

_PATTERN = re.compile(r"^(\d{9})RT(\d{4})$")
_TZ = ZoneInfo("America/Toronto")
_CACHE_KEY = "_tax_registration_rows"


def normalize_gst_hst(raw: Any) -> str:
    """Return ``'123456789 RT0001'`` or ``''``; raise ValueError on anything else."""
    text = re.sub(r"[\s-]+", "", str(raw or "")).upper()
    if not text:
        return ""
    m = _PATTERN.match(text)
    if not m:
        raise ValueError("GST/HST number must be 9 digits + RT and 4 digits, e.g. 123456789 RT0001")
    return f"{m.group(1)} RT{m.group(2)}"


def safe_gst_hst(raw: Any) -> str:
    """Valid number or '' (invalid stored values never reach a document)."""
    try:
        return normalize_gst_hst(raw)
    except ValueError:
        return ""


def normalize_finance(raw: Any) -> dict[str, Any]:
    """Finance settings no longer hold the GST/HST number (Settings > Tax registration does)."""
    if raw is not None and not isinstance(raw, dict):
        raise ValueError("finance settings must be an object")
    out = dict(raw or {})
    out.pop("gst_hst_number", None)
    return out


@dataclass(frozen=True)
class Registration:
    registered: bool
    gst_hst_number: str
    legal_name: str
    effective_from: date | None


NOT_REGISTERED = Registration(False, "", "", None)


def _day(at: Any) -> date:
    if at is None:
        return datetime.now(_TZ).date()
    if isinstance(at, datetime):
        aware = at if at.tzinfo else at.replace(tzinfo=UTC)
        return aware.astimezone(_TZ).date()
    if isinstance(at, date):
        return at
    raise TypeError("at must be a date or datetime")


def _rows(db: Any) -> list[Any]:
    info = getattr(db, "info", None)
    if isinstance(info, dict) and _CACHE_KEY in info:
        return info[_CACHE_KEY]
    try:
        from porterchain_api.admin_engine.tax_registrations import registration_rows

        rows = registration_rows(db)
    except Exception:  # table missing (old DB) or a mocked session: act as non-registrant
        rows = []
    rows = [r for r in rows if hasattr(r, "effective_from")]
    if isinstance(info, dict):
        info[_CACHE_KEY] = rows
    return rows


def clear_cache(db: Any) -> None:
    info = getattr(db, "info", None)
    if isinstance(info, dict):
        info.pop(_CACHE_KEY, None)


def registration_at(db: Any, at: Any = None) -> Registration:
    if db is None:
        return NOT_REGISTERED
    day = _day(at)
    current = None
    for row in _rows(db):
        if row.effective_from <= day:
            current = row
    if current is None:
        return NOT_REGISTERED
    number = safe_gst_hst(current.gst_hst_number)
    if not number:
        return Registration(False, "", "", current.effective_from)
    return Registration(True, number, (current.legal_name or "").strip(), current.effective_from)


def collects_tax(db: Any, at: Any = None) -> bool:
    return registration_at(db, at).registered


def supplier_gst_hst_number(db: Any, at: Any = None) -> str:
    return registration_at(db, at).gst_hst_number


def supplier_legal_name(db: Any, at: Any = None) -> str:
    return registration_at(db, at).legal_name


def history(db: Any) -> list[dict[str, Any]]:
    return [
        {
            "id": r.id,
            "gst_hst_number": safe_gst_hst(r.gst_hst_number) or None,
            "legal_name": r.legal_name,
            "effective_from": r.effective_from.isoformat(),
            "note": r.note,
            "created_by": r.created_by,
            "created_at": r.created_at.isoformat() if getattr(r, "created_at", None) else None,
        }
        for r in reversed(_rows(db))
    ]


def registration_status(db: Any) -> dict[str, Any]:
    now = registration_at(db)
    upcoming = [r for r in _rows(db) if r.effective_from > _day(None)]
    nxt = upcoming[0] if upcoming else None
    return {
        "registered": now.registered,
        "gst_hst_number": now.gst_hst_number,
        "legal_name": now.legal_name,
        "effective_from": now.effective_from.isoformat() if now.effective_from else None,
        # Back-compat for the old admin banner.
        "set": now.registered,
        "warning": None
        if now.registered
        else (
            "Not registered for GST/HST: the system charges and shows no GST/HST anywhere. "
            "Add your number in Admin > Finance > GST/HST once CRA issues it."
        ),
        "upcoming": {
            "gst_hst_number": safe_gst_hst(nxt.gst_hst_number) or None,
            "legal_name": nxt.legal_name,
            "effective_from": nxt.effective_from.isoformat(),
        }
        if nxt is not None
        else None,
        "history": history(db),
    }


def record_registration(
    db: Any,
    *,
    gst_hst_number: Any,
    legal_name: Any,
    effective_from: Any,
    actor_id: str | None,
    note: str | None = None,
) -> Any:
    """Append a registration change. Never edits an earlier row.

    ``gst_hst_number`` empty = deregistration from that date. A change may not be dated
    before the latest existing change (history stays in order; issued invoices are never
    re-taxed either way).
    """
    from porterchain_api.admin_engine.tax_registrations import add_registration

    number = normalize_gst_hst(gst_hst_number)
    name = str(legal_name or "").strip()
    if number and not name:
        raise ValueError("legal_name_required")
    if len(name) > 255:
        raise ValueError("legal_name_too_long")
    if isinstance(effective_from, str):
        try:
            effective_from = date.fromisoformat(effective_from)
        except ValueError:
            raise ValueError("effective_from_invalid") from None
    if not isinstance(effective_from, date):
        raise ValueError("effective_from_invalid")
    rows = _rows(db)
    if rows and effective_from < rows[-1].effective_from:
        raise ValueError("effective_from_before_latest_change")
    current = registration_at(db, effective_from)
    if current.gst_hst_number == number and (current.legal_name or "") == (name if number else ""):
        raise ValueError("registration_unchanged")
    row = add_registration(
        db,
        gst_hst_number=number or None,
        legal_name=name or None,
        effective_from=effective_from,
        note=(note or "").strip()[:500] or None,
        created_by=actor_id,
    )
    clear_cache(db)
    return row
