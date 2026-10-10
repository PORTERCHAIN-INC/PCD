"""Sequential, gap-free invoice numbers and Interac payment reference codes.

Numbers look like ``INV-2026-000123``. The counter row for ``prefix+year`` is
locked (``SELECT … FOR UPDATE``) and incremented inside the caller's transaction,
so a rolled-back invoice also rolls back its number: no gaps, no duplicates.
Legacy random numbers (``INV-YYYYMMDD-ABC123``) stay valid and are never rewritten.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

# No 0/O, 1/I/L: people type these codes into a banking app.
_REF_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
REFERENCE_PREFIX = "PC-"
REFERENCE_LENGTH = 5


def _scope(prefix: str, year: int) -> str:
    return f"{prefix}:{year}"[:32]


def _max_issued(db: Session, head: str, year: int) -> int:
    import re

    from porterchain_api.booking_models import Invoice

    pattern = re.compile(rf"^{re.escape(head)}-{year}-(\d{{6,}})$")
    best = 0
    for (num,) in db.query(Invoice.invoice_number).filter(Invoice.invoice_number.like(f"{head}-{year}-%")).all():
        m = pattern.match(num or "")
        if m:
            best = max(best, int(m.group(1)))
    return best


def allocate_invoice_number(db: Session, *, prefix: str | None = None, now: datetime | None = None) -> str:
    from porterchain_api.billing_engine.models import InvoiceNumberSequence

    head = (prefix or "INV").strip().upper() or "INV"
    year = (now or datetime.now(UTC)).year
    scope = _scope(head, year)
    row = db.execute(
        select(InvoiceNumberSequence).where(InvoiceNumberSequence.scope == scope).with_for_update()
    ).scalar_one_or_none()
    if row is None:
        # First number for this prefix/year (or the counter was lost, e.g. a migration
        # downgrade): continue after the highest number already issued, never collide.
        start_at = _max_issued(db, head, year)
        dialect = db.get_bind().dialect.name
        if dialect == "postgresql":
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            db.execute(
                pg_insert(InvoiceNumberSequence)
                .values(scope=scope, last_value=start_at)
                .on_conflict_do_nothing(index_elements=["scope"])
            )
        else:  # pragma: no cover - sqlite is not supported for integration tests
            db.add(InvoiceNumberSequence(scope=scope, last_value=start_at))
            db.flush()
        row = db.execute(
            select(InvoiceNumberSequence).where(InvoiceNumberSequence.scope == scope).with_for_update()
        ).scalar_one()
    row.last_value = int(row.last_value or 0) + 1
    db.flush()
    return f"{head}-{year}-{row.last_value:06d}"


def new_reference_code() -> str:
    return REFERENCE_PREFIX + "".join(secrets.choice(_REF_ALPHABET) for _ in range(REFERENCE_LENGTH))


def ensure_payment_reference(db: Session, invoice) -> str:
    """Give an invoice a unique PC-XXXXX code (idempotent)."""
    from porterchain_api.booking_models import Invoice

    if getattr(invoice, "payment_reference", None):
        return invoice.payment_reference
    for _ in range(20):
        code = new_reference_code()
        if not db.query(Invoice.id).filter(Invoice.payment_reference == code).first():
            invoice.payment_reference = code
            db.flush()
            return code
    raise RuntimeError("payment_reference_exhausted")  # pragma: no cover - 28M codes


def normalize_reference(text: str | None) -> str | None:
    """Find a PC-XXXXX code in free text (memo), tolerant of spaces/lowercase/missing dash."""
    import re

    if not text:
        return None
    m = re.search(r"\bPC[\s\-_:#]*([2-9A-HJKMNP-Z]{5})\b", text.upper())
    if not m:
        return None
    return REFERENCE_PREFIX + m.group(1)
