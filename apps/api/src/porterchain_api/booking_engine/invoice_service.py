"""Invoice finalization — auto-invoice after POD + receipt email payloads."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from porterchain_api.booking_engine import events as E
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.numbers import generate_invoice_number, generate_receipt_number
from porterchain_api.booking_engine.order_transitions import transition_order_state
from porterchain_api.domain.states import OrderState, PaymentStatus
from porterchain_api.booking_models import Customer, Invoice, Order, Payment

logger = logging.getLogger(__name__)

_BLOCKED_DOC_HOSTS = frozenset({"example.local", "example.com", "localhost", "127.0.0.1"})


def public_document_url(url: str | None) -> str | None:
    """Drop placeholder / non-http document links so Order 360 never opens dead hosts."""
    if not url or not isinstance(url, str):
        return None
    raw = url.strip()
    if not raw.lower().startswith(("http://", "https://")):
        return None
    try:
        host = (urlparse(raw).hostname or "").lower()
    except Exception:
        return None
    if not host or host in _BLOCKED_DOC_HOSTS or host.endswith(".example"):
        return None
    return raw


def _amount_display(cents: int | None, currency: str | None) -> str:
    cur = (currency or "cad").upper()
    return f"${(cents or 0) / 100:.2f} {cur}"


def _receipt_links(invoice: Invoice, payment: Payment | None) -> dict[str, Any]:
    receipt_url = public_document_url(
        invoice.stripe_receipt_url or (payment.receipt_url if payment else None)
    )
    return {
        "receipt_url": receipt_url,
        "invoice_pdf_url": public_document_url(invoice.pdf_url),
        "receipt_number": invoice.receipt_number,
    }


class InvoiceService:
    """Idempotent invoice create + INVOICED transition with email-ready events."""

    def finalize_after_pod(self, db: Session, order_id: str) -> Invoice | None:
        """Called on ``order.pod_completed`` — ensure invoice + email customer/merchant."""
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            logger.warning("invoice finalize: order_not_found %s", order_id)
            return None

        if order.state == OrderState.INVOICED.value:
            invoice = db.query(Invoice).filter(Invoice.order_id == order.id).first()
            return invoice

        if order.state != OrderState.POD_COMPLETED.value:
            return db.query(Invoice).filter(Invoice.order_id == order.id).first()

        invoice = self.ensure_invoice(db, order)
        db.flush()

        transition_order_state(
            db,
            order,
            OrderState.INVOICED,
            event_type=E.ORDER_INVOICED,
            actor_type="system",
            payload=self._invoice_event_payload(db, order, invoice),
        )
        db.refresh(order)
        return invoice

    def ensure_invoice(self, db: Session, order: Order, *, receipt_url: str | None = None) -> Invoice:
        payment = (
            db.query(Payment)
            .filter(Payment.order_id == order.id, Payment.status == PaymentStatus.SUCCEEDED.value)
            .order_by(Payment.created_at.desc())
            .first()
        )
        existing = db.query(Invoice).filter(Invoice.order_id == order.id).first()
        if existing:
            if receipt_url and not existing.stripe_receipt_url:
                existing.stripe_receipt_url = receipt_url
            if not existing.receipt_number:
                from porterchain_api.admin_engine.platform_settings import receipt_number_prefix

                existing.receipt_number = generate_receipt_number(prefix=receipt_number_prefix(db))
            from porterchain_api.billing_engine.invoice_document import attach_invoice_document

            attach_invoice_document(db, existing, order, payment)
            return existing

        from porterchain_api.admin_engine.platform_settings import (
            invoice_number_prefix,
            receipt_number_prefix,
            tax_cents_for_amount,
        )

        amount_cents = int(order.amount_cents or 0)
        invoice = Invoice(
            invoice_number=generate_invoice_number(prefix=invoice_number_prefix(db)),
            receipt_number=generate_receipt_number(prefix=receipt_number_prefix(db)),
            order_id=order.id,
            customer_id=order.customer_id,
            merchant_id=order.merchant_id,
            amount_cents=amount_cents,
            tax_cents=tax_cents_for_amount(db, amount_cents),
            fees_cents=0,
            currency=order.currency or "cad",
            stripe_receipt_url=receipt_url or (payment.receipt_url if payment else None),
            pdf_url=None,
        )
        db.add(invoice)
        db.flush()
        from porterchain_api.billing_engine.invoice_document import attach_invoice_document

        attach_invoice_document(db, invoice, order, payment)

        emit_event(
            db,
            event_type=E.INVOICE_CREATED,
            aggregate_type="invoice",
            aggregate_id=invoice.id,
            correlation_id=order.id,
            payload={"invoice_number": invoice.invoice_number},
        )
        emit_event(
            db,
            event_type=E.RECEIPT_GENERATED,
            aggregate_type="invoice",
            aggregate_id=invoice.id,
            correlation_id=order.id,
            payload={
                **self._invoice_event_payload(db, order, invoice),
                "payment_reference": payment.payment_reference if payment else None,
            },
        )
        return invoice

    def _invoice_event_payload(self, db: Session, order: Order, invoice: Invoice) -> dict[str, Any]:
        payment = (
            db.query(Payment)
            .filter(Payment.order_id == order.id)
            .order_by(Payment.created_at.desc())
            .first()
        )
        customer = (
            db.query(Customer).filter(Customer.id == order.customer_id).first()
            if order.customer_id
            else None
        )
        from porterchain_api.admin_engine.platform_settings import (
            platform_company_name,
            platform_support_email,
        )
        from porterchain_api.merchant_engine.lookups import get_merchant

        merchant = get_merchant(db, order.merchant_id)
        links = _receipt_links(invoice, payment)
        # Prefer customer email for retail; merchant billing email for B2B.
        email = (customer.email if customer else None) or (merchant.email if merchant else None)
        return {
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "order_id": order.id,
            "order_number": order.order_number,
            "tracking_number": order.tracking_number,
            "customer_id": order.customer_id,
            "merchant_id": order.merchant_id,
            "merchant_name": (merchant.company_name if merchant else None)
            or platform_company_name(db),
            "merchant_email": (merchant.email if merchant else None),
            "support_email": platform_support_email(db),
            "email": email,
            "amount_cents": invoice.amount_cents,
            "amount_display": _amount_display(invoice.amount_cents, invoice.currency),
            "currency": invoice.currency,
            **links,
        }

    def manual_invoice(self, db: Session, order_id: str, *, commit: bool = False) -> Invoice:
        """Admin Generate invoice — POD_COMPLETED → INVOICED (idempotent if already invoiced)."""
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise LookupError("order_not_found")
        if order.state == OrderState.INVOICED.value:
            invoice = db.query(Invoice).filter(Invoice.order_id == order.id).first()
            if not invoice:
                invoice = self.ensure_invoice(db, order)
        elif order.state != OrderState.POD_COMPLETED.value:
            raise ValueError(
                f"invoice_requires_pod_completed: current state is {order.state}"
            )
        else:
            invoice = self.finalize_after_pod(db, order_id)
            if not invoice:
                raise RuntimeError("invoice_finalize_failed")
        if commit:
            db.commit()
        return invoice

    def resend_receipt(self, db: Session, order_id: str, *, commit: bool = False) -> dict[str, Any]:
        """Re-emit receipt.generated so notification engine sends HTML receipt again."""
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise LookupError("order_not_found")
        invoice = db.query(Invoice).filter(Invoice.order_id == order.id).first()
        if not invoice:
            raise ValueError("invoice_not_found")
        payload = self._invoice_event_payload(db, order, invoice)
        emit_event(
            db,
            event_type=E.RECEIPT_GENERATED,
            aggregate_type="invoice",
            aggregate_id=invoice.id,
            correlation_id=order.id,
            payload=payload,
            publish=True,
        )
        # Synchronous delivery path (Mailpit / SMTP) — do not wait on Redis worker.
        try:
            from porterchain_api.notification_engine.event_router import handle_domain_event

            handle_domain_event(
                {
                    "event_type": E.RECEIPT_GENERATED,
                    "aggregate_type": "invoice",
                    "aggregate_id": invoice.id,
                    "correlation_id": order.id,
                    "payload": payload,
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("resend receipt notify failed order=%s: %s", order_id, exc)
        if commit:
            db.commit()
        return {
            "order_id": order.id,
            "invoice_number": invoice.invoice_number,
            "email": payload.get("email"),
            "receipt_url": payload.get("receipt_url"),
        }
