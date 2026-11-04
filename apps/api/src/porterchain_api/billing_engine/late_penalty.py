"""Late-payment penalty (owner decision 2026-10-30).

When a business invoice is still unpaid after its due date we add, ONCE, a penalty of
``late_penalty_pct`` (20%) of the billed amount and suspend the business the same day
(in-app notice + EN/FR email through the normal MERCHANT_SUSPENDED event).

* Idempotent: one ``billing_ledger_entries`` row per invoice, kind ``late_penalty``, with
  the unique idempotency key ``late_penalty:<invoice_id>``. Re-runs never add it twice.
* The penalty is carried in ``invoices.fees_cents`` (already additive in every total,
  outstanding balance, PDF and statement) and shown as its own line,
  "Late payment penalty (20%)". It is not taxed.
* Unsuspend is automatic once every penalised invoice is paid in full including the
  penalty (``auto_unsuspend``, run on record-payment and by the worker sweep); admins can
  still unsuspend by hand. ``unsuspend_candidates`` lists who qualifies.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from porterchain_api.billing_engine.models import BillingLedgerEntry
from porterchain_api.booking_models import Invoice, Order

KIND = "late_penalty"


def key_for(invoice_id: str) -> str:
    return f"{KIND}:{invoice_id}"


def label(pct: float) -> str:
    return f"Late payment penalty ({pct:g}%)"


def penalty_entry(db: Session, invoice_id: str) -> BillingLedgerEntry | None:
    return (
        db.query(BillingLedgerEntry)
        .filter(BillingLedgerEntry.idempotency_key == key_for(invoice_id))
        .first()
    )


def penalty_fields(db: Session, invoice: Invoice) -> dict[str, Any]:
    """``penalty_cents`` / ``penalty_label`` for invoice serializers (0 / None when none)."""
    e = penalty_entry(db, invoice.id)
    if not isinstance(e, BillingLedgerEntry):  # none (or a stubbed query in unit tests)
        return {"penalty_cents": 0, "penalty_label": None}
    pct = float((e.metadata_json or {}).get("pct") or 20)
    return {"penalty_cents": int(e.amount_cents or 0), "penalty_label": label(pct)}


def _status(db: Session, invoice: Invoice, now: datetime) -> str:
    from porterchain_api.billing_engine.merchant_service import (
        effective_payment_terms,
        invoice_status,
    )
    from porterchain_api.merchant_engine.lookups import get_merchant

    order = db.query(Order).filter(Order.id == invoice.order_id).first() if invoice.order_id else None
    merchant = get_merchant(db, invoice.merchant_id)
    terms = effective_payment_terms(order, merchant)
    return invoice_status(invoice, order, None, terms=terms, now=now.replace(tzinfo=None))


def _total_cents(invoice: Any) -> int:
    from porterchain_api.billing_engine.merchant_service import invoice_total_cents

    try:
        return int(invoice_total_cents(invoice))
    except Exception:  # noqa: BLE001 - notice copy must never block the suspend
        return 0


def _money(cents: int) -> str:
    return f"${cents / 100:,.2f}"


def suspend_for_penalty(db: Session, merchant: Any, invoice: Invoice) -> bool:
    """System suspend (same event, notice and email as an admin suspend). False if not active."""
    from porterchain_api.admin_engine import events as E
    from porterchain_api.booking_engine._core import emit_event
    from porterchain_api.domain.merchant_states import MerchantStatus
    from porterchain_api.merchant_engine.lifecycle import set_status

    if merchant is None or str(merchant.status or "").upper() != MerchantStatus.ACTIVE.value:
        return False
    set_status(merchant, MerchantStatus.SUSPENDED.value)
    emit_event(
        db,
        event_type=E.MERCHANT_SUSPENDED,
        aggregate_type="merchant",
        aggregate_id=merchant.id,
        actor_type="system",
        actor_id="late_penalty",
        payload={
            "merchant_id": merchant.id,
            "company_name": merchant.company_name,
            "merchant_email": _billing_email(merchant),
            "reason": "unpaid_invoice",
            "invoice_number": invoice.invoice_number,
            "amount_due": _money(_total_cents(invoice)),
            "penalty_amount": _money(int(getattr(invoice, "fees_cents", 0) or 0)),
        },
    )
    return True


def apply_due_penalties(
    db: Session, *, now: datetime | None = None, pct: float | None = None
) -> dict[str, int]:
    """Penalise every overdue business invoice once and suspend its business. Commits."""
    from porterchain_api.billing_engine.merchant_service import invoice_total_cents
    from porterchain_api.merchant_engine.lookups import get_merchant

    if pct is None:
        from porterchain_api.config import get_settings

        pct = float(get_settings().late_penalty_pct)
    now = now or datetime.now(UTC)
    out = {"scanned": 0, "penalised": 0, "suspended": 0}
    if pct <= 0:
        return out
    rows = (
        db.query(Invoice)
        .filter(
            Invoice.merchant_id.isnot(None),
            Invoice.paid_at.is_(None),
            Invoice.voided_at.is_(None),
            Invoice.status.notin_(("paid", "void", "cancelled", "credited", "draft")),
        )
        .all()
    )
    for inv in rows:
        out["scanned"] += 1
        if penalty_entry(db, inv.id) is not None:
            continue
        if _status(db, inv, now) != "overdue":
            continue
        locked = db.query(Invoice).filter(Invoice.id == inv.id).with_for_update().one()
        base = invoice_total_cents(locked)
        amount = int((Decimal(base) * Decimal(str(pct)) / 100).quantize(Decimal(1), ROUND_HALF_UP))
        if amount <= 0:
            continue
        try:
            with db.begin_nested():
                db.add(
                    BillingLedgerEntry(
                        kind=KIND,
                        invoice_id=locked.id,
                        merchant_id=locked.merchant_id,
                        amount_cents=amount,
                        currency=locked.currency or "cad",
                        idempotency_key=key_for(locked.id),
                        metadata_json={"pct": pct, "base_cents": base, "applied_at": now.isoformat()},
                    )
                )
                db.flush()
        except IntegrityError:
            continue  # another worker got there first
        locked.fees_cents = int(locked.fees_cents or 0) + amount
        out["penalised"] += 1
        if suspend_for_penalty(db, get_merchant(db, locked.merchant_id), locked):
            out["suspended"] += 1
        db.commit()
    return out


def _billing_email(merchant):
    """L66: overdue suspension / reinstatement are billing mail -> primary AP contact, else company email."""
    from porterchain_api.merchant_engine.invoice_reminder import primary_billing_email

    return primary_billing_email(merchant) or merchant.email


def unsuspend_candidates(db: Session, merchant_id: str | None = None) -> list[dict[str, Any]]:
    """Suspended businesses whose penalised invoices are now paid in full (penalty included)."""
    from porterchain_api.billing_engine.merchant_service import outstanding_cents
    from porterchain_api.domain.merchant_states import MerchantStatus
    from porterchain_api.merchant_models import Merchant

    out = []
    q = db.query(Merchant).filter(Merchant.status.in_([MerchantStatus.SUSPENDED.value, "suspended"]))
    if merchant_id:
        q = q.filter(Merchant.id == merchant_id)
    for m in q.all():
        entries = db.query(BillingLedgerEntry).filter(
            BillingLedgerEntry.kind == KIND, BillingLedgerEntry.merchant_id == m.id
        ).all()
        if not entries:
            continue
        owed = 0
        for e in entries:
            inv = db.get(Invoice, e.invoice_id)
            if inv is not None:
                owed += outstanding_cents(inv, _status(db, inv, datetime.now(UTC)))
        if owed == 0:
            out.append({"merchant_id": m.id, "company_name": m.company_name})
    return out


def auto_unsuspend(db: Session, merchant_id: str | None = None, *, commit: bool = True) -> list[str]:
    """Ravi's rule: once everything penalised is paid in full (penalty included), reinstate the
    business automatically. Same unsuspend event as admin, so the business gets an in-app notice
    and the EN/FR "account reinstated" email. Only businesses suspended for a late penalty qualify."""
    from porterchain_api.admin_engine import events as E
    from porterchain_api.booking_engine._core import emit_event
    from porterchain_api.domain.merchant_states import MerchantStatus
    from porterchain_api.merchant_engine.lifecycle import set_status
    from porterchain_api.merchant_engine.lookups import get_merchant

    done: list[str] = []
    for c in unsuspend_candidates(db, merchant_id):
        m = get_merchant(db, c["merchant_id"])
        if m is None:
            continue
        set_status(m, MerchantStatus.ACTIVE.value)
        emit_event(
            db,
            event_type=E.MERCHANT_UNSUSPENDED,
            aggregate_type="merchant",
            aggregate_id=m.id,
            actor_type="system",
            actor_id="late_penalty",
            payload={
                "merchant_id": m.id,
                "company_name": m.company_name,
                "merchant_email": _billing_email(m),
                "reason": "paid_in_full",
            },
        )
        done.append(m.id)
    if done and commit:
        db.commit()
    return done
