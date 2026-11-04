"""Merchant pays an invoice by card: Stripe Checkout (hosted page, PorterChain never sees the card).

Completion is idempotent and reachable two ways: the Stripe webhook
(``checkout.session.completed`` with ``metadata.purpose == "merchant_invoice"``) and the
portal's return-page sync (``sync_invoice_checkout``) for local stacks without webhooks.
Paying in full also reinstates a business suspended for a late penalty.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import Settings

logger = logging.getLogger(__name__)

PURPOSE = "merchant_invoice"


def card_payments_available(settings: Settings) -> bool:
    """Ravi 2026-11-03: merchant (B2B) invoices are paid by Interac e-Transfer only.
    Stripe card checkout stays for customer (direct) bookings. The old flag
    ``merchant_card_payments_enabled`` no longer turns merchant card checkout on; the
    completion/sync paths stay so a session opened earlier still settles once."""
    return False


def _outstanding(db: Session, invoice: Any) -> int:
    from porterchain_api.billing_engine.merchant_service import invoice_status, outstanding_cents
    from porterchain_api.booking_models import Order

    order = db.get(Order, invoice.order_id) if invoice.order_id else None
    status = invoice_status(invoice, order, None, terms=order.payment_terms if order else None)
    return int(outstanding_cents(invoice, status))


def _invoice_for(db: Session, merchant_id: str, invoice_id: str) -> Any:
    from porterchain_api.booking_models import Invoice

    inv = db.get(Invoice, invoice_id)
    if inv is None or inv.merchant_id != merchant_id:
        raise LookupError("invoice_not_found")
    return inv


def create_invoice_checkout(db: Session, settings: Settings, merchant: Any, invoice_id: str, email: str | None) -> dict[str, Any]:
    if not card_payments_available(settings):
        raise ValueError("card_payments_unavailable")
    inv = _invoice_for(db, merchant.id, invoice_id)
    amount = _outstanding(db, inv)
    if amount <= 0:
        raise ValueError("nothing_outstanding")
    from porterchain_services.stripe import sdk as stripe_sdk

    stripe_sdk.configure(settings.stripe_secret)
    portal = settings.merchant_portal_url.rstrip("/")
    meta = {"purpose": PURPOSE, "invoice_id": inv.id, "merchant_id": merchant.id,
            "invoice_number": inv.invoice_number or "", "amount_cents": str(amount)}
    kwargs: dict[str, Any] = {
        "mode": "payment",
        "line_items": [{"price_data": {"currency": inv.currency or "cad", "unit_amount": amount,
                                        "product_data": {"name": f"PorterChain invoice {inv.invoice_number}"}},
                        "quantity": 1}],
        "success_url": f"{portal}/billing/invoices/{inv.id}?card=done&session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{portal}/billing/invoices/{inv.id}?card=cancelled",
        "metadata": meta,
        "payment_intent_data": {"metadata": meta},
    }
    if email:
        kwargs["customer_email"] = email
    session = stripe_sdk.create_checkout_session(**kwargs)
    return {"url": session.url, "session_id": session.id, "amount_cents": amount}


def complete_invoice_checkout(db: Session, session: dict[str, Any]) -> dict[str, Any]:
    """Record the card payment once. Returns {"status": paid|partial|already_paid|unpaid|ignored}."""
    meta = session.get("metadata") or {}
    if meta.get("purpose") != PURPOSE or not meta.get("invoice_id"):
        return {"status": "ignored"}
    if session.get("payment_status") != "paid":
        return {"status": "unpaid"}
    from porterchain_api.booking_models import Payment

    intent = session.get("payment_intent")
    intent_id = intent.get("id") if isinstance(intent, dict) else intent
    txn = f"stripe:{intent_id or session.get('id')}"
    if db.query(Payment).filter(Payment.transaction_id == txn).first():
        return {"status": "already_paid"}
    from porterchain_api.admin_engine.merchant_ar_service import MerchantArService

    try:
        out = MerchantArService().record_payment(
            db, None, meta["invoice_id"], method="card", amount_cents=int(session.get("amount_total") or 0) or None,
            reference=(intent_id or "")[-32:] or None, online_card=True, transaction_id=txn,
            source={"stripe_checkout_session": session.get("id")}, commit=False,
        )
    except ValueError as exc:
        if str(exc) in {"already_paid", "nothing_outstanding"}:
            return {"status": "already_paid"}
        raise
    from porterchain_api.billing_engine.late_penalty import auto_unsuspend

    reinstated = bool(meta.get("merchant_id")) and bool(auto_unsuspend(db, meta["merchant_id"], commit=False))
    db.commit()
    return {**out, "merchant_reinstated": reinstated}


def sync_invoice_checkout(db: Session, settings: Settings, merchant: Any, invoice_id: str, session_id: str) -> dict[str, Any]:
    _invoice_for(db, merchant.id, invoice_id)
    if not settings.stripe_secret:
        raise ValueError("card_payments_unavailable")
    from porterchain_api.services.stripe_service import retrieve_checkout_session

    session = retrieve_checkout_session(settings, session_id)
    meta = session.get("metadata") or {}
    if meta.get("invoice_id") != invoice_id or meta.get("merchant_id") != merchant.id:
        raise LookupError("invoice_not_found")
    return complete_invoice_checkout(db, session)
