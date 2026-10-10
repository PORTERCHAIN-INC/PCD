"""Stripe invoice refund with idempotency (ENG-G2 split from finance_service)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.billing_engine.models import BillingLedgerEntry
from porterchain_api.booking_models import Invoice, Order


def refund_invoice(
    svc: Any,
    db: Session,
    ctx: AdminContext,
    settings: Any,
    invoice_id: str,
    *,
    amount_cents: int | None = None,
) -> dict[str, Any]:
    from porterchain_api.services.stripe_service import create_refund

    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise LookupError("invoice_not_found")
    order = db.query(Order).filter(Order.id == invoice.order_id).first() if invoice.order_id else None
    if not order:  # cycle (Interac) invoices are not Stripe-refundable
        raise LookupError("order_not_found")
    payment = svc._payment_for_order(db, invoice.order_id)
    pi = payment.stripe_payment_intent_id if payment and payment.stripe_payment_intent_id else order.stripe_payment_intent_id
    if not pi:
        raise ValueError("refund_requires_stripe_payment")
    if not order.stripe_payment_intent_id:
        order.stripe_payment_intent_id = pi
    captured = int(payment.amount_cents if payment and payment.amount_cents else invoice.amount_cents)
    settled = int(amount_cents) if amount_cents and amount_cents > 0 else captured
    claim_key = f"refund:{invoice.id}:{settled}"
    claim = (
        db.query(BillingLedgerEntry)
        .filter(BillingLedgerEntry.idempotency_key == claim_key)
        .first()
    )
    if claim and claim.status == "recorded":
        return {
            "invoice_id": invoice.id,
            "refund_id": (claim.metadata_json or {}).get("stripe_refund_id"),
            "status": "REFUNDED" if settled >= captured else "PARTIAL",
            "amount_cents": settled,
        }
    if claim is None:
        claim = BillingLedgerEntry(
            kind="refund",
            payment_id=payment.id if payment else None,
            invoice_id=invoice.id,
            order_id=order.id,
            merchant_id=invoice.merchant_id or order.merchant_id,
            amount_cents=settled,
            currency=invoice.currency or "cad",
            status="pending",
            idempotency_key=claim_key,
            metadata_json={"created_by": ctx.user.id},
        )
        db.add(claim)
        db.commit()
        db.refresh(claim)
    try:
        refund_id = create_refund(settings, order, settled, idempotency_key=claim_key)
    except Exception:
        claim.status = "failed"
        db.commit()
        raise
    if not refund_id:
        claim.status = "failed"
        db.commit()
        raise ValueError("stripe_refund_unavailable")
    claim.status = "recorded"
    claim.metadata_json = {**(claim.metadata_json or {}), "stripe_refund_id": refund_id}
    if payment and settled >= captured:
        payment.status = "REFUNDED"
    log_admin_audit(
        db,
        ctx,
        action="finance.refund",
        resource_type="invoice",
        resource_id=invoice.id,
        payload={"refund_id": refund_id, "amount_cents": settled},
    )
    db.commit()
    return {
        "invoice_id": invoice.id,
        "refund_id": refund_id,
        "status": "REFUNDED" if settled >= captured else "PARTIAL",
        "amount_cents": settled,
    }
