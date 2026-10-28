"""Email the recipient a credit note: customer-friendly reason only, never the staff note."""

from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
_EMAIL = re.compile(r"([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+)")


def mask_email(text: str | None) -> str:
    """``alice@example.com`` -> ``a***@example.com`` for logs (PIPEDA 4.7)."""
    return _EMAIL.sub(r"\1***@\2", text or "")


def _recipient_email(db: Session, note: Any) -> str | None:
    from porterchain_api.booking_models import Customer

    if note.customer_id:
        c = db.get(Customer, note.customer_id)
        if c is not None and c.email:
            return c.email
    if note.merchant_id:
        from porterchain_api.merchant_engine.invoice_reminder import primary_billing_email
        from porterchain_api.merchant_engine.lookups import get_merchant

        m = get_merchant(db, note.merchant_id)
        if m is not None:
            return primary_billing_email(m)
    return None


def document_url(note: Any) -> str:
    from porterchain_api.config import get_settings

    s = get_settings()
    if note.customer_id:
        return f"{s.customer_portal_url.rstrip('/')}/invoices/{note.invoice_id}"
    return f"{s.merchant_portal_url.rstrip('/')}/billing/invoices/{note.invoice_id}"


def send_credit_note_email(db: Session, note: Any) -> dict[str, Any]:
    from porterchain_api.admin_engine.platform_settings import platform_support_email
    from porterchain_api.billing_engine.merchant_service import invoice_status, outstanding_cents
    from porterchain_api.booking_engine.invoice_service import _amount_display
    from porterchain_api.booking_models import Invoice, Order
    from porterchain_api.reporting.credit_note_pdf import _date
    from porterchain_api.reporting.order_documents import _issuer_from_db, _province_tax_label

    to = _recipient_email(db, note)
    if not to:
        logger.info("credit note %s: no recipient email", note.credit_note_number)
        return {"sent": False, "reason": "no_recipient"}
    invoice = db.get(Invoice, note.invoice_id)
    order = db.get(Order, invoice.order_id) if invoice and invoice.order_id else None
    status = invoice_status(invoice, order, None, terms=(order.payment_terms if order else None))
    cur = note.currency
    settle = ""
    if note.settlement == "credit_balance":
        settle = f"{_amount_display(note.settlement_cents, cur)} added to your account credit, applied to your next invoice."
    elif note.settlement and note.settlement.startswith("stripe_refund"):
        settle = f"{_amount_display(note.settlement_cents, cur)} refunded to your original payment card."
    _, legal, _ = _issuer_from_db(db)
    ctx = {
        "credit_note_number": note.credit_note_number,
        "invoice_number": note.original_invoice_number,
        "invoice_date": _date(note.original_invoice_date),
        "recipient_name": note.recipient_name or "there",
        "customer_reason": note.customer_reason,
        "subtotal_display": _amount_display(note.subtotal_cents, cur),
        "tax_display": _amount_display(note.tax_cents, cur),
        "tax_label": _province_tax_label(db, note.tax_province) or "GST/HST",
        # Non-registrant (or untaxed original invoice): no tax lines at all.
        "tax_lines": (
            f"Credit before tax: {_amount_display(note.subtotal_cents, cur)}\n"
            f"Tax reversed ({_province_tax_label(db, note.tax_province) or 'GST/HST'}): "
            f"{_amount_display(note.tax_cents, cur)}\n"
            if int(note.tax_cents or 0) > 0
            else ""
        ),
        "itc_line": (
            " If you claimed an input tax credit for the original invoice, reduce it by the tax shown."
            if int(note.tax_cents or 0) > 0
            else ""
        ),
        "amount_display": _amount_display(note.amount_cents, cur),
        "balance_display": _amount_display(outstanding_cents(invoice, status), cur),
        "settlement_line": settle,
        "document_url": document_url(note),
        "support_email": platform_support_email(db),
        "supplier_legal_name": legal,
    }
    try:
        from porterchain_api.notification_engine.delivery_service import DeliveryService

        log = DeliveryService().deliver(
            {
                "channel": "email",
                "template": "invoice_credit_note_issued",
                "recipient": to,
                "recipient_type": "customer" if note.customer_id else "merchant",
                "recipient_id": note.customer_id or note.merchant_id or "",
                "context": ctx,
            }
        )
        status_out = getattr(log, "status", "sent")
    except Exception:
        logger.warning("credit note email failed (credit_note=%s, to=%s)", note.credit_note_number, mask_email(to), exc_info=True)
        return {"sent": False, "reason": "delivery_failed", "recipient": mask_email(to)}
    logger.info("credit note %s emailed to %s (%s)", note.credit_note_number, mask_email(to), status_out)
    return {"sent": status_out in ("sent", "delivered"), "status": status_out, "recipient": mask_email(to)}
