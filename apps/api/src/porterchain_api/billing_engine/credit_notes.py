"""Issue merchant credit notes (not a full GL)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.billing_engine.ar import CREDIT_NOTE_KIND
from porterchain_api.billing_engine.models import BillingLedgerEntry, CreditNote


def issue_credit_note(
    db: Session,
    *,
    merchant_id: str | None,
    invoice_id: str | None,
    amount_cents: int,
    reason: str | None = None,
    status: str = "open",
    flush: bool = True,
) -> CreditNote:
    cents = int(amount_cents)
    if cents <= 0:
        raise ValueError("credit_note_amount_invalid")
    note = CreditNote(
        merchant_id=merchant_id,
        invoice_id=invoice_id,
        amount_cents=cents,
        reason=reason,
        status=status,
    )
    db.add(note)
    db.add(
        BillingLedgerEntry(
            kind=CREDIT_NOTE_KIND,
            invoice_id=invoice_id,
            merchant_id=merchant_id,
            amount_cents=cents,
            status="recorded",
            metadata_json={"reason": reason} if reason else {},
        )
    )
    if flush:
        db.flush()
    return note
