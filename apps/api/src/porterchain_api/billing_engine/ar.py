"""One outstanding number per merchant (BD).

Outstanding = open invoices + delivered-but-uninvoiced work − credit notes.

Admin Merchant 360, the merchant Billing page, and collections all read this
module so the three screens cannot quote different cents. Delivery AR only —
CRM sales invoices (``crm_invoices``) are a separate ledger and never land here.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import or_
from sqlalchemy.orm import Session

from porterchain_api.billing_engine.merchant_service import (
    effective_payment_terms,
    invoice_status,
    outstanding_cents,
)
from porterchain_api.billing_engine.models import BillingLedgerEntry
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_models import Merchant
from porterchain_api.booking_models import Invoice, Order, Payment

CREDIT_NOTE_KIND = "credit_note"

# Work on these orders is never billable, so it is not outstanding either.
_NOT_BILLABLE = frozenset({OrderState.CANCELLED.value, OrderState.REFUNDED.value})

#: Standard AR aging ladder, as an accountant reads it. Upper bound in days,
#: inclusive; the last bucket is everything beyond.
AGING_LADDER: tuple[tuple[int, str], ...] = (
    (0, "Current"),
    (30, "1–30 days"),
    (60, "31–60 days"),
    (90, "61–90 days"),
)
AGING_OLDEST = "90+ days"


def aging_bucket(days_overdue: int) -> str:
    """English aging bucket for a number of days past due (BL)."""
    for upper, label in AGING_LADDER:
        if days_overdue <= upper:
            return label
    return AGING_OLDEST


@dataclass(frozen=True)
class MerchantAr:
    """Delivery AR for one merchant. ``outstanding_cents`` is the number to show."""

    merchant_id: str
    invoiced_cents: int = 0
    uninvoiced_cents: int = 0
    credits_cents: int = 0
    overdue_cents: int = 0
    open_invoice_count: int = 0
    overdue_invoice_count: int = 0

    @property
    def outstanding_cents(self) -> int:
        return max(0, self.invoiced_cents + self.uninvoiced_cents - self.credits_cents)


def _latest_payment_by_order(db: Session, order_ids: list[str]) -> dict[str, Payment]:
    if not order_ids:
        return {}
    latest: dict[str, Payment] = {}
    rows = (
        db.query(Payment)
        .filter(Payment.order_id.in_(order_ids))
        .order_by(Payment.created_at.asc())
        .all()
    )
    for pay in rows:
        if pay.order_id:
            latest[pay.order_id] = pay
    return latest


def merchant_ar_index(
    db: Session,
    *,
    merchant_ids: Iterable[str] | None = None,
) -> dict[str, MerchantAr]:
    """Delivery AR for every requested merchant, in a handful of queries.

    Merchants with no orders are omitted; callers should treat a miss as zero.
    """
    ids = sorted({str(m) for m in merchant_ids}) if merchant_ids is not None else None
    if ids is not None and not ids:
        return {}

    order_q = db.query(Order).filter(Order.merchant_id.isnot(None))
    if ids is not None:
        order_q = order_q.filter(Order.merchant_id.in_(ids))
    orders = order_q.all()
    if not orders:
        return {}

    by_order = {o.id: o for o in orders}
    order_ids = list(by_order)
    found_ids = sorted({str(o.merchant_id) for o in orders if o.merchant_id})

    merchants = {m.id: m for m in db.query(Merchant).filter(Merchant.id.in_(found_ids)).all()}
    payments = _latest_payment_by_order(db, order_ids)

    invoiced: dict[str, int] = {}
    overdue: dict[str, int] = {}
    open_counts: dict[str, int] = {}
    overdue_counts: dict[str, int] = {}
    invoiced_order_ids: set[str] = set()

    for inv in db.query(Invoice).filter(Invoice.order_id.in_(order_ids)).all():
        order = by_order.get(inv.order_id or "")
        if order is None or not order.merchant_id:
            continue
        invoiced_order_ids.add(order.id)
        mid = str(order.merchant_id)
        status = invoice_status(
            inv,
            order,
            payments.get(order.id),
            terms=effective_payment_terms(order, merchants.get(mid)),
        )
        cents = outstanding_cents(inv, status)
        if cents <= 0:
            continue
        invoiced[mid] = invoiced.get(mid, 0) + cents
        open_counts[mid] = open_counts.get(mid, 0) + 1
        if status == "overdue":
            overdue[mid] = overdue.get(mid, 0) + cents
            overdue_counts[mid] = overdue_counts.get(mid, 0) + 1

    uninvoiced: dict[str, int] = {}
    for order in orders:
        if order.id in invoiced_order_ids or order.state in _NOT_BILLABLE:
            continue
        mid = str(order.merchant_id)
        uninvoiced[mid] = uninvoiced.get(mid, 0) + int(order.amount_cents or 0)

    credits: dict[str, int] = {}
    credit_rows = (
        db.query(BillingLedgerEntry)
        .filter(
            BillingLedgerEntry.kind == CREDIT_NOTE_KIND,
            or_(
                BillingLedgerEntry.merchant_id.in_(found_ids),
                BillingLedgerEntry.order_id.in_(order_ids),
            ),
        )
        .all()
    )
    for entry in credit_rows:
        order = by_order.get(entry.order_id or "")
        mid = str(entry.merchant_id or (order.merchant_id if order else "") or "")
        if mid not in merchants:
            continue
        credits[mid] = credits.get(mid, 0) + int(entry.amount_cents or 0)

    return {
        mid: MerchantAr(
            merchant_id=mid,
            invoiced_cents=invoiced.get(mid, 0),
            uninvoiced_cents=uninvoiced.get(mid, 0),
            credits_cents=credits.get(mid, 0),
            overdue_cents=overdue.get(mid, 0),
            open_invoice_count=open_counts.get(mid, 0),
            overdue_invoice_count=overdue_counts.get(mid, 0),
        )
        for mid in found_ids
    }


def merchant_ar(db: Session, merchant: Merchant | str) -> MerchantAr:
    """Delivery AR for one merchant. Same cents on every screen."""
    merchant_id = str(merchant if isinstance(merchant, str) else merchant.id)
    index = merchant_ar_index(db, merchant_ids=[merchant_id])
    return index.get(merchant_id, MerchantAr(merchant_id=merchant_id))


def delivery_ar_total_cents(db: Session) -> int:
    """Every merchant's outstanding delivery AR. Excludes CRM sales invoices."""
    return sum(ar.outstanding_cents for ar in merchant_ar_index(db).values())
