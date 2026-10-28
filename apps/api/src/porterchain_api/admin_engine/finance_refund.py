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


# --- Invoice credit notes (void / line / partial). Rules: docs/compliance/INVOICE_ADJUSTMENTS_CANADA.md


def _credit_note_audit(db: Session, ctx: AdminContext, action: str, note: Any) -> None:
    log_admin_audit(
        db,
        ctx,
        action=action,
        resource_type="invoice",
        resource_id=note.invoice_id,
        payload={
            "credit_note_id": note.id,
            "credit_note_number": note.credit_note_number,
            "kind": note.kind,
            "reason_code": note.reason_code,
            "internal_note": note.internal_note,
            "amount_cents": int(note.amount_cents or 0),
            "tax_cents": int(note.tax_cents or 0),
            "status": note.status,
            "settlement": note.settlement,
            "settlement_cents": int(note.settlement_cents or 0),
        },
    )


def _credit_note_after_issue(db: Session, settings: Any, ctx: AdminContext, note: Any) -> dict:
    """Refund the card when needed, then email the recipient. Runs after commit."""
    from porterchain_api.billing_engine import invoice_adjustments as adj
    from porterchain_api.platform.credit_note_email import send_credit_note_email

    if note.status != "issued":
        return {"sent": False, "reason": "pending_approval"}
    if note.settlement == "stripe_refund_pending":
        adj.settle_stripe_refund(db, settings, note, actor_id=ctx.user.id)
    return send_credit_note_email(db, note)


def credit_note_out(db: Session, note: Any, email: dict | None = None) -> dict:
    from porterchain_api.billing_engine import invoice_adjustments as adj

    invoice = db.get(Invoice, note.invoice_id)
    data = adj.serialize(note, internal=True)
    if invoice is not None:
        data["warning"] = adj.tax_reason_warning(note, invoice)
        data["invoice"] = adj.adjustment_summary(db, invoice)
    data["email"] = email
    return data


def invoice_adjustments(db: Session, invoice_id: str) -> dict:
    from porterchain_api.billing_engine import invoice_adjustments as adj

    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise LookupError("invoice_not_found")
    return adj.adjustment_summary(db, invoice)


def create_credit_note(db: Session, settings: Any, ctx: AdminContext, invoice_id: str, **kw: Any) -> dict:
    from porterchain_api.billing_engine import invoice_adjustments as adj

    try:
        note = adj.request_credit(db, invoice_id=invoice_id, actor_id=ctx.user.id, **kw)
    except Exception:
        db.rollback()
        raise
    action = "finance.credit_note.issued" if note.status == "issued" else "finance.credit_note.requested"
    _credit_note_audit(db, ctx, action, note)
    db.commit()
    db.refresh(note)
    return credit_note_out(db, note, _credit_note_after_issue(db, settings, ctx, note))


def approve_credit_note(db: Session, settings: Any, ctx: AdminContext, credit_note_id: str) -> dict:
    from porterchain_api.billing_engine import invoice_adjustments as adj

    try:
        note = adj.approve_credit(db, credit_note_id=credit_note_id, actor_id=ctx.user.id)
    except Exception:
        db.rollback()
        raise
    _credit_note_audit(db, ctx, "finance.credit_note.approved", note)
    db.commit()
    db.refresh(note)
    return credit_note_out(db, note, _credit_note_after_issue(db, settings, ctx, note))


def reject_credit_note(db: Session, ctx: AdminContext, credit_note_id: str, note_text: str | None) -> dict:
    from porterchain_api.billing_engine import invoice_adjustments as adj

    try:
        note = adj.reject_credit(db, credit_note_id=credit_note_id, actor_id=ctx.user.id, note_text=note_text)
    except Exception:
        db.rollback()
        raise
    _credit_note_audit(db, ctx, "finance.credit_note.rejected", note)
    db.commit()
    return credit_note_out(db, note)


def retry_credit_note_refund(db: Session, settings: Any, ctx: AdminContext, credit_note_id: str) -> dict:
    from porterchain_api.billing_engine import invoice_adjustments as adj
    from porterchain_api.billing_engine.models import CreditNote

    note = db.get(CreditNote, credit_note_id)
    if note is None:
        raise LookupError("credit_note_not_found")
    if note.settlement not in ("stripe_refund_pending", "stripe_refund_failed"):
        raise ValueError("credit_note_no_refund_pending")
    adj.settle_stripe_refund(db, settings, note, actor_id=ctx.user.id)
    _credit_note_audit(db, ctx, "finance.credit_note.refund_retry", note)
    db.commit()
    return credit_note_out(db, note)


def credit_note_pdf_for_admin(db: Session, credit_note_id: str) -> tuple[bytes, str]:
    from porterchain_api.billing_engine.models import CreditNote
    from porterchain_api.reporting.credit_note_pdf import credit_note_pdf

    note = db.get(CreditNote, credit_note_id)
    if note is None:
        raise LookupError("credit_note_not_found")
    return credit_note_pdf(db, note)
