"""Cycle-invoice extras for Admin finance views: lines, offline payments, ledger scope."""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from porterchain_api.billing_engine.models import BillingLedgerEntry, InvoiceLine
from porterchain_api.booking_models import Invoice, Order, Payment


def invoice_line_count(db: Session, invoice: Invoice) -> int:
    if (getattr(invoice, "billing_kind", None) or "order") != "cycle":
        return 1
    return int(db.query(InvoiceLine).filter(InvoiceLine.invoice_id == invoice.id).count())


def invoice_payment_fields(db: Session, invoice: Invoice) -> dict[str, Any]:
    return {
        "amount_paid_cents": int(getattr(invoice, "amount_paid_cents", 0) or 0),
        "payment_reference": getattr(invoice, "payment_reference", None),
        "billing_kind": getattr(invoice, "billing_kind", None) or "order",
        "order_count": invoice_line_count(db, invoice),
    }


def invoice_ledger_filter(invoice: Invoice):
    match = [BillingLedgerEntry.invoice_id == invoice.id]
    if invoice.order_id:
        match.append(BillingLedgerEntry.order_id == invoice.order_id)
    return or_(*match)


def invoice_detail_extras(db: Session, invoice: Invoice) -> dict[str, Any]:
    lines = []
    rows = (
        db.query(InvoiceLine)
        .filter(InvoiceLine.invoice_id == invoice.id)
        .order_by(InvoiceLine.created_at.asc())
        .all()
    )
    for ln in rows:
        order = db.get(Order, ln.order_id) if ln.order_id else None
        lines.append(
            {
                "order_id": ln.order_id,
                "order_number": order.order_number if order else None,
                "description": ln.description,
                "amount_cents": int(ln.amount_cents or 0),
                "tax_cents": int(ln.tax_cents or 0),
            }
        )
    payments = (
        db.query(Payment)
        .filter(Payment.invoice_id == invoice.id, Payment.status == "SUCCEEDED")
        .order_by(Payment.created_at.asc())
        .all()
    )
    return {
        "lines": lines,
        "offline_payments": [
            {
                "payment_id": p.id,
                "amount_cents": int(p.amount_cents or 0),
                "method": p.payment_method,
                "reference": p.payment_reference,
                "created_at": p.created_at,
            }
            for p in payments
        ],
    }
