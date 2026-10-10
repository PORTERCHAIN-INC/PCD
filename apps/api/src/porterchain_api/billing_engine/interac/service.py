"""Ingest parsed Interac transfers into the review queue; approve/reject with audit."""

from __future__ import annotations

from datetime import UTC, datetime
from email.message import Message
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.platform.admin_audit import log_admin_audit
from porterchain_api.billing_engine.interac.auth import verify_interac_sender
from porterchain_api.billing_engine.interac.matcher import propose_match
from porterchain_api.billing_engine.interac.parser import NotInteracEmail, parse_interac_email
from porterchain_api.billing_engine.models import InteracTransfer

OPEN_STATUSES = ("proposed", "needs_review", "suspicious")


def ingest_message(db: Session, msg: Message, *, authserv_id: str) -> InteracTransfer | None:
    """Parse one email. Returns the queued row, or None if it is not an Interac payment
    or was already ingested. Never applies money."""
    try:
        parsed = parse_interac_email(msg)
    except NotInteracEmail:
        return None
    if db.query(InteracTransfer.id).filter(InteracTransfer.message_id == parsed.message_id).first():
        return None
    verdict = verify_interac_sender(msg, authserv_id=authserv_id)
    row = InteracTransfer(
        message_id=parsed.message_id,
        kind=parsed.kind,
        received_at=parsed.received_at,
        sender_name=parsed.sender_name,
        sender_email=parsed.sender_email,
        amount_cents=parsed.amount_cents,
        currency=parsed.currency,
        memo=parsed.memo,
        interac_reference=parsed.interac_reference,
        auth_ok=verdict.ok,
        auth_detail=verdict.detail[:255],
    )
    dup = (
        db.query(InteracTransfer)
        .filter(
            InteracTransfer.interac_reference.isnot(None),
            InteracTransfer.interac_reference == parsed.interac_reference,
        )
        .first()
        if parsed.interac_reference
        else None
    )
    if dup is not None:
        row.status = "duplicate"
        row.match_note = f"same Interac reference as {dup.id}"
    elif not verdict.ok:
        row.status = "suspicious"
        row.match_note = "sender not verified — do not approve"
    else:
        proposal = propose_match(
            db,
            amount_cents=parsed.amount_cents,
            memo=parsed.memo,
            sender_name=parsed.sender_name,
            sender_email=parsed.sender_email,
        )
        row.invoice_id = proposal.invoice_id
        row.merchant_id = proposal.merchant_id
        row.match_method = proposal.method
        row.match_note = proposal.note
        # Exact matches are "proposed" (one click). Partial/over/unmatched need a human look.
        row.status = "proposed" if proposal.invoice_id and proposal.note == "exact" else "needs_review"
    db.add(row)
    db.flush()
    log_admin_audit(
        db,
        None,
        action="finance.interac.ingest",
        resource_type="interac_transfer",
        resource_id=row.id,
        payload={"status": row.status, "amount_cents": row.amount_cents, "auth": row.auth_detail},
    )
    return row


def transfer_row(db: Session, t: InteracTransfer) -> dict[str, Any]:
    from porterchain_api.booking_models import Invoice
    from porterchain_api.platform.merchant_billing import merchant_display_name

    inv = db.get(Invoice, t.invoice_id) if t.invoice_id else None
    outstanding = None
    if inv is not None:
        from porterchain_api.billing_engine.merchant_service import invoice_status, outstanding_cents

        outstanding = outstanding_cents(inv, invoice_status(inv, None, None))
    return {
        "id": t.id,
        "kind": t.kind,
        "status": t.status,
        "received_at": t.received_at,
        "sender_name": t.sender_name,
        "sender_email": t.sender_email,
        "amount_cents": t.amount_cents,
        "currency": t.currency,
        "memo": t.memo,
        "interac_reference": t.interac_reference,
        "auth_ok": bool(t.auth_ok),
        "auth_detail": t.auth_detail,
        "invoice_id": t.invoice_id,
        "invoice_number": inv.invoice_number if inv else None,
        "invoice_reference": inv.payment_reference if inv else None,
        "invoice_outstanding_cents": outstanding,
        "merchant_id": t.merchant_id,
        "merchant_name": merchant_display_name(db, t.merchant_id),
        "match_method": t.match_method,
        "match_note": t.match_note,
        "payment_id": t.payment_id,
        "reviewed_by": t.reviewed_by,
        "reviewed_at": t.reviewed_at,
        "review_note": t.review_note,
    }


def list_transfers(db: Session, *, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    q = db.query(InteracTransfer)
    if status == "open":
        q = q.filter(InteracTransfer.status.in_(OPEN_STATUSES))
    elif status:
        q = q.filter(InteracTransfer.status == status)
    rows = q.order_by(InteracTransfer.created_at.desc()).limit(max(1, min(limit, 500))).all()
    return [transfer_row(db, t) for t in rows]


def approve_transfer(
    db: Session, ctx, transfer_id: str, *, invoice_id: str | None = None, note: str | None = None
) -> dict[str, Any]:
    from porterchain_api.platform.merchant_billing import record_offline_payment

    t = db.query(InteracTransfer).filter(InteracTransfer.id == transfer_id).with_for_update().first()
    if t is None:
        raise LookupError("transfer_not_found")
    if t.status not in ("proposed", "needs_review"):
        raise ValueError(f"not_approvable:{t.status}")
    if not t.auth_ok:
        raise ValueError("sender_not_verified")
    target = invoice_id or t.invoice_id
    if not target:
        raise ValueError("invoice_required")
    result = record_offline_payment(
        db,
        ctx,
        target,
        method="interac",
        amount_cents=int(t.amount_cents),
        reference=t.interac_reference or t.memo,
        paid_at=t.received_at,
        source={"interac_transfer_id": t.id, "match_method": t.match_method if target == t.invoice_id else "manual"},
        commit=False,
    )
    if target != t.invoice_id:
        t.match_method = "manual"
    t.invoice_id = target
    t.status = "approved"
    t.payment_id = result["payment_id"]
    t.reviewed_by = ctx.user.id
    t.reviewed_at = datetime.now(UTC)
    t.review_note = (note or "")[:255] or None
    log_admin_audit(
        db,
        ctx,
        action="finance.interac.approve",
        resource_type="interac_transfer",
        resource_id=t.id,
        payload={
            "invoice_id": target,
            "payment_id": result["payment_id"],
            "amount_cents": t.amount_cents,
            "applied_cents": result["applied_cents"],
            "excess_cents": result["excess_cents"],
            "match_method": t.match_method,
        },
    )
    db.commit()
    return {**transfer_row(db, t), "payment": result}


def reject_transfer(db: Session, ctx, transfer_id: str, *, note: str | None = None) -> dict[str, Any]:
    t = db.query(InteracTransfer).filter(InteracTransfer.id == transfer_id).with_for_update().first()
    if t is None:
        raise LookupError("transfer_not_found")
    if t.status in ("approved", "rejected"):
        raise ValueError(f"not_rejectable:{t.status}")
    t.status = "rejected"
    t.reviewed_by = ctx.user.id
    t.reviewed_at = datetime.now(UTC)
    t.review_note = (note or "")[:255] or None
    log_admin_audit(
        db,
        ctx,
        action="finance.interac.reject",
        resource_type="interac_transfer",
        resource_id=t.id,
        payload={"note": t.review_note},
    )
    db.commit()
    return transfer_row(db, t)
