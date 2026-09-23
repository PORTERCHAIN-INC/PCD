"""Persist invoice status and lines so AR is not Python-only."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from porterchain_api.billing_engine.merchant_service import invoice_status
from porterchain_api.billing_engine.models import BillingLedgerEntry, InvoiceLine
from porterchain_api.booking_models import Invoice, Order, Payment


def persist_invoice_status(
    invoice: Invoice,
    order: Order | None,
    payment: Payment | None,
    *,
    terms: str | None = None,
    now: datetime | None = None,
) -> str:
    status = invoice_status(invoice, order, payment, terms=terms, now=now)
    invoice.status = status
    stamp = now or datetime.now(UTC)
    if invoice.issued_at is None:
        invoice.issued_at = invoice.created_at or stamp
    if status == "paid" and invoice.paid_at is None:
        invoice.paid_at = stamp
    if status in ("void", "cancelled") and invoice.voided_at is None:
        invoice.voided_at = stamp
    return status


def _delivery_description(order: Order | None) -> str:
    if order is None:
        return "Delivery"
    meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
    vehicle = str(meta.get("vehicle_class") or "Delivery")
    if meta.get("booking_mode") == "vehicle":
        return f"{vehicle} · Whole vehicle"
    items = []
    parcels = meta.get("parcels")
    if isinstance(parcels, dict):
        items = parcels.get("items") or []
    count = len(items) if isinstance(items, list) else 0
    if count:
        return f"{vehicle} · {count} parcel{'s' if count != 1 else ''}"
    return "Delivery"


def ensure_invoice_line(db: Session, invoice: Invoice, order: Order | None) -> InvoiceLine:
    description = _delivery_description(order)
    existing = db.query(InvoiceLine).filter(InvoiceLine.invoice_id == invoice.id).first()
    if existing:
        existing.amount_cents = int(invoice.amount_cents or 0)
        existing.tax_cents = int(invoice.tax_cents or 0)
        if order and not existing.order_id:
            existing.order_id = order.id
        if not existing.description or existing.description == "Delivery":
            existing.description = description
        return existing
    line = InvoiceLine(
        invoice_id=invoice.id,
        order_id=order.id if order else invoice.order_id,
        description=_delivery_description(order),
        amount_cents=int(invoice.amount_cents or 0),
        tax_cents=int(invoice.tax_cents or 0),
    )
    db.add(line)
    db.flush()
    return line


def attach_invoice_document(
    db: Session,
    invoice: Invoice,
    order: Order | None,
    payment: Payment | None = None,
    *,
    terms: str | None = None,
) -> Invoice:
    persist_invoice_status(invoice, order, payment, terms=terms)
    ensure_invoice_line(db, invoice, order)
    if payment is not None:
        payment.invoice_id = invoice.id
    if order is not None:
        (
            db.query(BillingLedgerEntry)
            .filter(
                BillingLedgerEntry.order_id == order.id,
                BillingLedgerEntry.invoice_id.is_(None),
            )
            .update({"invoice_id": invoice.id}, synchronize_session=False)
        )
    return invoice
