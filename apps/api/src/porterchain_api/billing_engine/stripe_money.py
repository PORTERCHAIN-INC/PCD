"""Stripe money that moves outside PCD: dashboard refunds, disputes, fees and payouts.

* ``charge.refunded`` / ``charge.refund.updated``: a refund made in the Stripe dashboard
  is written to the billing ledger once (keyed by Stripe refund id). Refunds PCD started
  itself are already in the ledger with that id, so they are never counted twice.
* ``charge.dispute.*``: one ledger row per dispute, updated as Stripe moves it along;
  the payment is marked DISPUTED, then back to SUCCEEDED (won) or DISPUTE_LOST.
* ``payout.*``: each bank payout is stored and, once paid, reconciled against its balance
  transactions: gross − fees − refunds − disputes ± other must equal the payout.

Everything here is read from Stripe; nothing calls Stripe to move money.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable

from sqlalchemy.orm import Session

from porterchain_api.billing_engine.models import BillingLedgerEntry, StripePayout
from porterchain_api.booking_models import Invoice, Payment


def _pi_id(obj: dict[str, Any]) -> str | None:
    pi = obj.get("payment_intent")
    if isinstance(pi, dict):
        pi = pi.get("id")
    return str(pi) if pi else None


def _payment_for(db: Session, obj: dict[str, Any]) -> Payment | None:
    pi = _pi_id(obj)
    if not pi:
        return None
    return (
        db.query(Payment)
        .filter(Payment.stripe_payment_intent_id == pi)
        .order_by(Payment.created_at.desc())
        .first()
    )


def _invoice_for(db: Session, payment: Payment | None) -> Invoice | None:
    if payment is None:
        return None
    if payment.invoice_id:
        return db.get(Invoice, payment.invoice_id)
    if payment.order_id:
        return db.query(Invoice).filter(Invoice.order_id == payment.order_id).first()
    return None


def _audit(db: Session, action: str, resource_id: str, payload: dict[str, Any]) -> None:
    from porterchain_api.platform.admin_audit import log_admin_audit

    log_admin_audit(db, None, action=action, resource_type="payment", resource_id=resource_id, payload=payload)


def _ts(raw: Any) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(raw), tz=UTC) if raw else None
    except (TypeError, ValueError, OSError):
        return None


def apply_charge_refunds(db: Session, charge: dict[str, Any]) -> dict[str, Any]:
    payment = _payment_for(db, charge)
    if payment is None:
        return {"status": "no_payment"}
    invoice = _invoice_for(db, payment)
    refunds = ((charge.get("refunds") or {}).get("data")) or []
    known = {
        (e.metadata_json or {}).get("stripe_refund_id")
        for e in db.query(BillingLedgerEntry).filter(
            BillingLedgerEntry.kind == "refund", BillingLedgerEntry.payment_id == payment.id
        )
    } | {
        (e.idempotency_key or "").removeprefix("stripe_refund:")
        for e in db.query(BillingLedgerEntry).filter(BillingLedgerEntry.idempotency_key.like("stripe_refund:%"))
    }
    added = 0
    for r in refunds:
        rid = r.get("id")
        if not rid or rid in known or r.get("status") in ("failed", "canceled"):
            continue
        db.add(
            BillingLedgerEntry(
                kind="refund",
                payment_id=payment.id,
                invoice_id=invoice.id if invoice else None,
                order_id=payment.order_id,
                merchant_id=invoice.merchant_id if invoice else None,
                amount_cents=int(r.get("amount") or 0),
                currency=(r.get("currency") or payment.currency or "cad").lower(),
                status="recorded",
                idempotency_key=f"stripe_refund:{rid}",
                metadata_json={"stripe_refund_id": rid, "source": "stripe_dashboard", "reason": r.get("reason")},
            )
        )
        added += 1
    refunded = int(charge.get("amount_refunded") or 0)
    if refunded and refunded >= int(charge.get("amount") or payment.amount_cents or 0):
        payment.status = "REFUNDED"
    if added:
        _audit(db, "finance.stripe.refund_synced", payment.id, {"refunds_added": added, "amount_refunded": refunded})
    db.flush()
    return {"status": "ok", "refunds_added": added, "amount_refunded_cents": refunded}


DISPUTE_OPEN = frozenset(
    {"warning_needs_response", "warning_under_review", "needs_response", "under_review"}
)


def apply_dispute(db: Session, dispute: dict[str, Any]) -> dict[str, Any]:
    did = dispute.get("id")
    if not did:
        return {"status": "no_id"}
    payment = _payment_for(db, dispute)
    invoice = _invoice_for(db, payment)
    status = str(dispute.get("status") or "needs_response")
    key = f"stripe_dispute:{did}"
    row = db.query(BillingLedgerEntry).filter(BillingLedgerEntry.idempotency_key == key).first()
    meta = {
        "stripe_dispute_id": did,
        "reason": dispute.get("reason"),
        "evidence_due_by": ((dispute.get("evidence_details") or {}).get("due_by")),
        "charge": dispute.get("charge") if isinstance(dispute.get("charge"), str) else None,
    }
    if row is None:
        row = BillingLedgerEntry(
            kind="stripe_dispute",
            payment_id=payment.id if payment else None,
            invoice_id=invoice.id if invoice else None,
            order_id=payment.order_id if payment else None,
            merchant_id=invoice.merchant_id if invoice else None,
            amount_cents=int(dispute.get("amount") or 0),
            currency=str(dispute.get("currency") or "cad").lower(),
            idempotency_key=key,
            status=status,
            metadata_json=meta,
        )
        db.add(row)
    else:
        row.status = status
        row.metadata_json = {**(row.metadata_json or {}), **{k: v for k, v in meta.items() if v}}
    if payment is not None:
        if status in DISPUTE_OPEN:
            payment.status = "DISPUTED"
        elif status == "won":
            payment.status = "SUCCEEDED"
        elif status == "lost":
            payment.status = "DISPUTE_LOST"
    _audit(db, "finance.stripe.dispute", payment.id if payment else did, {"dispute_id": did, "status": status})
    db.flush()
    return {"status": status, "dispute_id": did}


def upsert_payout(db: Session, payout: dict[str, Any]) -> StripePayout:
    pid = str(payout["id"])
    row = db.query(StripePayout).filter(StripePayout.stripe_payout_id == pid).first()
    if row is None:
        row = StripePayout(stripe_payout_id=pid, amount_cents=0, status="pending")
        db.add(row)
    row.status = str(payout.get("status") or row.status)
    row.amount_cents = int(payout.get("amount") or 0)
    row.currency = str(payout.get("currency") or "cad").lower()
    row.arrival_date = _ts(payout.get("arrival_date")) or row.arrival_date
    db.flush()
    return row


def reconcile_payout(
    db: Session, row: StripePayout, transactions: list[dict[str, Any]]
) -> StripePayout:
    """Split a payout into gross / fees / refunds / disputes and match charges to payments.

    Balance transaction amounts are signed cents. Per Stripe, a payout's own transaction
    (type ``payout``) is excluded; everything else nets to the payout amount.
    """
    gross = fees = refunds = disputes = other = 0
    matched = unmatched = 0
    for t in transactions:
        typ = str(t.get("type") or "")
        if typ == "payout":
            continue
        amount = int(t.get("amount") or 0)
        fee = int(t.get("fee") or 0)
        fees += fee
        if typ in ("charge", "payment"):
            gross += amount
            src = t.get("source") if isinstance(t.get("source"), dict) else {}
            payment = _payment_for(db, src) if src else None
            if payment is None:
                unmatched += 1
                continue
            matched += 1
            key = f"stripe_fee:{t.get('id')}"
            if fee and not db.query(BillingLedgerEntry.id).filter(BillingLedgerEntry.idempotency_key == key).first():
                db.add(
                    BillingLedgerEntry(
                        kind="stripe_fee",
                        payment_id=payment.id,
                        order_id=payment.order_id,
                        amount_cents=fee,
                        currency=str(t.get("currency") or "cad").lower(),
                        idempotency_key=key,
                        status="recorded",
                        metadata_json={"balance_transaction": t.get("id"), "payout": row.stripe_payout_id},
                    )
                )
        elif typ in ("refund", "payment_refund"):
            refunds += amount  # negative
        elif typ in ("adjustment", "dispute") or typ.startswith("dispute"):
            disputes += amount
        else:
            other += amount
    net = gross - fees + refunds + disputes + other
    row.gross_cents, row.fee_cents, row.refund_cents = gross, fees, -refunds
    row.dispute_cents, row.other_cents = -disputes, other
    row.matched_count, row.unmatched_count = matched, unmatched
    row.difference_cents = int(row.amount_cents) - net
    row.reconciled_at = datetime.now(UTC)
    db.flush()
    return row


def handle_payout_event(
    db: Session, payout: dict[str, Any], *, fetch: Callable[[str], list[dict[str, Any]]] | None
) -> dict[str, Any]:
    row = upsert_payout(db, payout)
    if row.status == "paid" and fetch is not None:
        reconcile_payout(db, row, fetch(row.stripe_payout_id))
    return {"status": row.status, "difference_cents": row.difference_cents}


def payouts_payload(db: Session, *, limit: int = 30) -> list[dict[str, Any]]:
    rows = db.query(StripePayout).order_by(StripePayout.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "stripe_payout_id": r.stripe_payout_id,
            "status": r.status,
            "amount_cents": r.amount_cents,
            "arrival_date": r.arrival_date,
            "gross_cents": r.gross_cents,
            "fee_cents": r.fee_cents,
            "refund_cents": r.refund_cents,
            "dispute_cents": r.dispute_cents,
            "other_cents": r.other_cents,
            "matched_count": r.matched_count,
            "unmatched_count": r.unmatched_count,
            "difference_cents": r.difference_cents,
            "reconciled": r.reconciled_at is not None and (r.difference_cents or 0) == 0,
            "reconciled_at": r.reconciled_at,
        }
        for r in rows
    ]


def disputes_payload(db: Session, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = (
        db.query(BillingLedgerEntry)
        .filter(BillingLedgerEntry.kind == "stripe_dispute")
        .order_by(BillingLedgerEntry.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "dispute_id": (r.metadata_json or {}).get("stripe_dispute_id"),
            "status": r.status,
            "open": r.status in DISPUTE_OPEN,
            "amount_cents": r.amount_cents,
            "reason": (r.metadata_json or {}).get("reason"),
            "evidence_due_by": _ts((r.metadata_json or {}).get("evidence_due_by")),
            "payment_id": r.payment_id,
            "invoice_id": r.invoice_id,
            "created_at": r.created_at,
        }
        for r in rows
    ]
