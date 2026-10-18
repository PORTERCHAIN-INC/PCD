"""Invoice line helpers — admin e2e / finance may call without importing billing_engine."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


def ensure_invoice_line(db: Session, invoice: Any, order: Any) -> Any:
    from porterchain_api.billing_engine.invoice_document import (
        ensure_invoice_line as _ensure,
    )

    return _ensure(db, invoice, order)


def invoice_lines_for(db: Session, invoice_id: str) -> list[Any]:
    from porterchain_api.billing_engine.models import InvoiceLine

    return db.query(InvoiceLine).filter(InvoiceLine.invoice_id == invoice_id).all()


def invoice_for_order(db: Session, order_id: str) -> Any:
    """Per-order invoice (``Invoice.order_id``) or the cycle invoice carrying the order's line."""
    from porterchain_api.billing_engine.models import InvoiceLine
    from porterchain_api.booking_models import Invoice

    inv = db.query(Invoice).filter(Invoice.order_id == order_id).first()
    if inv is not None:
        return inv
    return (
        db.query(Invoice)
        .join(InvoiceLine, InvoiceLine.invoice_id == Invoice.id)
        .filter(InvoiceLine.order_id == order_id)
        .first()
    )
