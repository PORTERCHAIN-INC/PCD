"""Merchant credit balance from overpayments, kept in the billing ledger.

``merchant_credit`` entries add credit (an Interac overpayment), ``merchant_credit_applied``
entries consume it (credit used to settle a later invoice). Balance = added − applied.
Credit *limits* and holds belong to the merchant-admin module, not here.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.billing_engine.models import BillingLedgerEntry

CREDIT_ADDED = "merchant_credit"
CREDIT_APPLIED = "merchant_credit_applied"


def _sum(db: Session, kind: str, merchant_id: str | None = None) -> int:
    q = db.query(func.coalesce(func.sum(BillingLedgerEntry.amount_cents), 0)).filter(
        BillingLedgerEntry.kind == kind
    )
    if merchant_id:
        q = q.filter(BillingLedgerEntry.merchant_id == merchant_id)
    return int(q.scalar() or 0)


def merchant_credit_cents(db: Session, merchant_id: str) -> int:
    return max(0, _sum(db, CREDIT_ADDED, merchant_id) - _sum(db, CREDIT_APPLIED, merchant_id))


def merchant_credit_total_cents(db: Session) -> int:
    return max(0, _sum(db, CREDIT_ADDED) - _sum(db, CREDIT_APPLIED))


def add_merchant_credit(
    db: Session, *, merchant_id: str, amount_cents: int, source: dict[str, Any]
) -> BillingLedgerEntry:
    entry = BillingLedgerEntry(
        kind=CREDIT_ADDED,
        merchant_id=merchant_id,
        amount_cents=int(amount_cents),
        status="available",
        metadata_json=source,
    )
    db.add(entry)
    db.flush()
    return entry
