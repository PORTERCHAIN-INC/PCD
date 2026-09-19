"""Merchant billing engine — net terms, cycles, invoice status, exports (masterrule §11)."""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime, timedelta
from typing import Any

from porterchain_api.domain.states import OrderState, PaymentTerms
from porterchain_api.merchant_models import Merchant
from porterchain_api.booking_models import Invoice, Order, Payment

NET_TERMS_DAYS: dict[str, int] = {
    PaymentTerms.IMMEDIATE.value: 0,
    PaymentTerms.NET_7.value: 7,
    PaymentTerms.NET_14.value: 14,
    PaymentTerms.NET_15.value: 15,
    PaymentTerms.NET_30.value: 30,
    PaymentTerms.NET_45.value: 45,
    PaymentTerms.CUSTOM.value: 30,
}

BILLING_CYCLES = ("WEEKLY", "BIWEEKLY", "MONTHLY", "CUSTOM")


def merchant_uses_stripe(merchant: Merchant) -> bool:
    """Contract / net-terms merchants skip Stripe unless explicitly configured."""
    if getattr(merchant, "stripe_enabled", False) is True:
        return True
    profile = merchant.profile if isinstance(merchant.profile, dict) else {}
    if profile.get("stripe_enabled") is True:
        return True
    if profile.get("stripe_checkout") is True:
        return True
    terms = (merchant.payment_terms or "").upper()
    return terms in ("IMMEDIATE", "STRIPE", "CREDIT_CARD")


def net_terms_days(terms: str | None) -> int:
    if not terms:
        return NET_TERMS_DAYS[PaymentTerms.NET_30.value]
    key = terms.upper().replace("-", "_")
    if key.startswith("NET") and key[3:].isdigit():
        return int(key[3:])
    return NET_TERMS_DAYS.get(key, NET_TERMS_DAYS[PaymentTerms.NET_30.value])


def invoice_due_date(created_at: datetime | None, terms: str | None) -> datetime | None:
    if not created_at:
        return None
    base = created_at.replace(tzinfo=None) if created_at.tzinfo else created_at
    return base + timedelta(days=net_terms_days(terms))


def payment_for_order(payment: Payment | None) -> Payment | None:
    return payment


def invoice_status(
    invoice: Invoice,
    order: Order | None,
    payment: Payment | None,
    *,
    terms: str | None = None,
    now: datetime | None = None,
) -> str:
    now = now or datetime.now(UTC).replace(tzinfo=None)
    if order and order.state in (OrderState.CANCELLED.value, OrderState.REFUNDED.value):
        return "cancelled"
    if payment:
        if payment.status == "SUCCEEDED":
            return "paid"
        if payment.status == "REFUNDED":
            return "void"
        if payment.status in ("PENDING", "PROCESSING", "FAILED"):
            return "pending"
    if getattr(invoice, "due_at", None):
        due = invoice.due_at.replace(tzinfo=None) if invoice.due_at.tzinfo else invoice.due_at
    else:
        due = invoice_due_date(invoice.created_at, terms or (order.payment_terms if order else None))
    if due and now > due:
        return "overdue"
    return "sent"


def invoice_total_cents(invoice: Invoice) -> int:
    """Gross invoice total for Admin/AR serializers.

    ``amount_cents`` is the charged amount (includes tax when ``tax_cents`` is a
    breakdown of that amount). Fees are always additive.
    """
    return int(invoice.amount_cents or 0) + int(invoice.fees_cents or 0)


def outstanding_cents(invoice: Invoice, status: str) -> int:
    if status in ("paid", "void", "cancelled"):
        return 0
    return invoice_total_cents(invoice)


def effective_payment_terms(order: Order | None, merchant: object | None) -> str | None:
    """Terms agreed on the order win; the merchant default is the fallback (BD).

    Only matters for legacy invoices with no ``due_at`` — but every screen must
    use the same precedence or due dates and overdue status drift apart.
    """
    order_terms = getattr(order, "payment_terms", None) if order else None
    if order_terms:
        return str(order_terms)
    merchant_terms = getattr(merchant, "payment_terms", None) if merchant else None
    return str(merchant_terms) if merchant_terms else None


def billing_period_bounds(
    cycle: str,
    reference: datetime | None = None,
    *,
    anchor: datetime | None = None,
) -> tuple[datetime, datetime]:
    ref = (reference or datetime.now(UTC)).replace(tzinfo=None)
    cycle_u = (cycle or "MONTHLY").upper()

    if cycle_u == "WEEKLY":
        start = datetime.combine((ref - timedelta(days=ref.weekday())).date(), datetime.min.time())
        end = start + timedelta(days=7)
        return start, end

    if cycle_u == "BIWEEKLY":
        anchor_dt = (anchor or ref).replace(tzinfo=None)
        days_since = (ref.date() - anchor_dt.date()).days
        period_index = max(days_since // 14, 0)
        start = anchor_dt + timedelta(days=period_index * 14)
        if start > ref:
            start = anchor_dt + timedelta(days=max(period_index - 1, 0) * 14)
        end = start + timedelta(days=14)
        return start, end

    if cycle_u == "CUSTOM":
        # Custom terms: calendar month default; override via merchant.profile.billing_period_days
        start = datetime(ref.year, ref.month, 1)
        if ref.month == 12:
            end = datetime(ref.year + 1, 1, 1)
        else:
            end = datetime(ref.year, ref.month + 1, 1)
        return start, end

    # MONTHLY default
    start = datetime(ref.year, ref.month, 1)
    if ref.month == 12:
        end = datetime(ref.year + 1, 1, 1)
    else:
        end = datetime(ref.year, ref.month + 1, 1)
    return start, end


def serialize_invoice_row(
    invoice: Invoice,
    order: Order | None,
    payment: Payment | None,
    *,
    terms: str | None = None,
    include_stripe: bool = False,
) -> dict[str, Any]:
    status = invoice_status(invoice, order, payment, terms=terms)
    due = invoice_due_date(invoice.created_at, terms or (order.payment_terms if order else None))
    if getattr(invoice, "due_at", None):
        due = invoice.due_at.replace(tzinfo=None) if invoice.due_at.tzinfo else invoice.due_at
    outstanding = outstanding_cents(invoice, status)
    row = {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "receipt_number": invoice.receipt_number,
        "order_id": invoice.order_id,
        "order_number": order.order_number if order else None,
        "tracking_number": order.tracking_number if order else None,
        "amount_cents": invoice.amount_cents,
        "tax_cents": invoice.tax_cents,
        "fees_cents": invoice.fees_cents,
        "outstanding_cents": outstanding,
        "currency": invoice.currency,
        "status": status,
        "payment_terms": terms or (order.payment_terms if order else "NET_30"),
        "due_date": due.isoformat() if due else None,
        "last_reminded_at": invoice.last_reminded_at.isoformat() if getattr(invoice, "last_reminded_at", None) else None,
        "pdf_url": invoice.pdf_url,
        "created_at": invoice.created_at,
    }
    if include_stripe and invoice.stripe_receipt_url:
        row["stripe_receipt_url"] = invoice.stripe_receipt_url
    return row


def build_tax_summary(invoices: list[Invoice]) -> dict[str, Any]:
    subtotal = sum(inv.amount_cents - inv.tax_cents for inv in invoices)
    tax = sum(inv.tax_cents for inv in invoices)
    fees = sum(inv.fees_cents for inv in invoices)
    return {
        "subtotal_cents": int(subtotal),
        "tax_cents": int(tax),
        "fees_cents": int(fees),
        "total_cents": int(subtotal + tax + fees),
        "invoice_count": len(invoices),
        "currency": invoices[0].currency if invoices else "cad",
    }


def rows_to_csv(rows: list[dict[str, Any]], fieldnames: list[str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    return buffer.getvalue()
