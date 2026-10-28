"""Stripe Checkout amount for a retail invoice after credit notes.

If a retail invoice is credited while its card checkout is still open, the open
Stripe session (old amount) is expired and a new one is created at the balance
after credits. A $0 balance means no checkout at all.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

OPEN = ("PENDING", "PROCESSING")


def invoice_balance_cents(db: Session, invoice: Any) -> int:
    from porterchain_api.booking_models import Order
    from porterchain_api.platform.invoice_status import invoice_status, outstanding_cents

    order = db.get(Order, invoice.order_id) if getattr(invoice, "order_id", None) else None
    status = invoice_status(invoice, order, None, terms=(order.payment_terms if order else None))
    return int(outstanding_cents(invoice, status))


def checkout_amount_cents(db: Session, quote: Any) -> int:
    """What Stripe should charge for this quote: the invoice balance once an invoice exists."""
    from porterchain_api.booking_models import Invoice, Order

    order = db.query(Order).filter(Order.quote_id == quote.id).first() if getattr(quote, "id", None) else None
    invoice = db.query(Invoice).filter(Invoice.order_id == order.id).first() if order else None
    if invoice is None:
        return int(quote.amount_cents or 0)
    return invoice_balance_cents(db, invoice)


def _open_payments(db: Session, invoice: Any) -> list[Any]:
    from sqlalchemy import or_

    from porterchain_api.booking_models import Payment

    conds = [Payment.invoice_id == invoice.id]
    if getattr(invoice, "order_id", None):
        conds.append(Payment.order_id == invoice.order_id)
    return (
        db.query(Payment)
        .filter(or_(*conds), Payment.status.in_(OPEN), Payment.stripe_checkout_session_id.isnot(None))
        .all()
    )


def reprice_open_checkouts(db: Session, settings: Any, invoice: Any) -> dict[str, Any]:
    """Expire open sessions for ``invoice``; open one new session at the balance if > 0.

    Flushes only; the caller commits.
    """
    from porterchain_api.booking_models import Customer, Payment, Quote
    from porterchain_api.services.stripe_service import create_checkout_session, expire_checkout_session

    payments = _open_payments(db, invoice)
    if not payments:
        return {"expired": 0, "new_session_id": None, "amount_cents": None}
    balance = invoice_balance_cents(db, invoice)
    mock = bool(getattr(settings, "allow_stripe_mock", False))
    for p in payments:
        if not mock:
            expire_checkout_session(settings, p.stripe_checkout_session_id)
        p.status = "CANCELLED"
        p.failure_reason = "repriced_after_credit_note"
    db.flush()
    new_id = None
    src = payments[-1]
    quote = db.get(Quote, src.quote_id) if src.quote_id else None
    customer = db.get(Customer, src.customer_id) if src.customer_id else None
    if balance > 0 and quote is not None and customer is not None:
        pay = Payment(
            quote_id=src.quote_id,
            order_id=src.order_id,
            customer_id=src.customer_id,
            invoice_id=invoice.id,
            status="PROCESSING",
            amount_cents=balance,
            currency=src.currency,
        )
        db.add(pay)
        db.flush()
        if mock:
            new_id = f"cs_mock_{pay.id}"
        else:
            _, new_id = create_checkout_session(settings, quote, customer, pay.id, amount_cents=balance)
        pay.stripe_checkout_session_id = new_id
        quote.stripe_checkout_session_id = new_id
        db.flush()
    return {"expired": len(payments), "new_session_id": new_id, "amount_cents": balance}
