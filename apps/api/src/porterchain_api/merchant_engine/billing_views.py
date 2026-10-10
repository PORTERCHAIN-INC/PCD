"""Merchant billing views — list/export helpers extracted from billing_service (ENG-G2)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from porterchain_api.admin_models import MerchantContract
from porterchain_api.billing_engine.merchant_service import (
    build_tax_summary,
    rows_to_csv,
)
from porterchain_api.billing_engine.models import BillingLedgerEntry
from porterchain_api.booking_models import Invoice, Order, Payment
from porterchain_api.merchant_engine.rbac import MerchantContext


def list_payments(svc: Any, db: Session, ctx: MerchantContext) -> list[dict[str, Any]]:
    rows = (
        db.query(Payment, Order)
        .join(Order, Payment.order_id == Order.id)
        .filter(Order.merchant_id == ctx.merchant.id)
        .order_by(Payment.created_at.desc())
        .limit(200)
        .all()
    )
    out: list[dict[str, Any]] = []
    for pay, order in rows:
        item = {
            "payment_id": pay.id,
            "order_id": order.id,
            "order_number": order.order_number,
            "tracking_number": order.tracking_number,
            "amount_cents": pay.amount_cents,
            "currency": pay.currency,
            "status": pay.status,
            "payment_method": pay.payment_method
            or ("stripe" if pay.stripe_payment_intent_id else "net_terms"),
            "payment_reference": pay.payment_reference,
            "created_at": pay.created_at.isoformat() if pay.created_at else None,
        }
        if pay.receipt_url:
            item["receipt_url"] = pay.receipt_url
        out.append(item)
    return out


def list_credit_notes(svc: Any, db: Session, ctx: MerchantContext) -> list[dict[str, Any]]:
    order_ids = [r[0] for r in svc._merchant_order_ids(db, ctx.merchant.id).all()]
    clauses = [BillingLedgerEntry.merchant_id == ctx.merchant.id]
    if order_ids:
        clauses.append(BillingLedgerEntry.order_id.in_(order_ids))
    entries = (
        db.query(BillingLedgerEntry)
        .filter(BillingLedgerEntry.kind == "credit_note", or_(*clauses))
        .order_by(BillingLedgerEntry.created_at.desc())
        .limit(100)
        .all()
    )
    result = []
    for e in entries:
        order = db.query(Order).filter(Order.id == e.order_id).first()
        result.append(
            {
                "credit_note_id": e.id,
                "order_id": e.order_id,
                "order_number": order.order_number if order else None,
                "tracking_number": order.tracking_number if order else None,
                "amount_cents": e.amount_cents,
                "currency": e.currency,
                "reason": (e.metadata_json or {}).get("reason"),
                "status": e.status,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
        )
    return result


def billing_history(svc: Any, db: Session, ctx: MerchantContext) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    for inv_row in svc.list_invoices_enriched(db, ctx):
        history.append(
            {
                "kind": "invoice",
                "id": inv_row["invoice_id"],
                "reference": inv_row["invoice_number"],
                "description": f"Invoice {inv_row['invoice_number']}",
                "amount_cents": inv_row["amount_cents"],
                "outstanding_cents": inv_row["outstanding_cents"],
                "status": inv_row["status"],
                "occurred_at": inv_row["created_at"],
            }
        )
    for pay in svc.list_payments(db, ctx):
        history.append(
            {
                "kind": "payment",
                "id": pay["payment_id"],
                "reference": pay.get("payment_reference"),
                "description": f"Payment for {pay.get('order_number')}",
                "amount_cents": -pay["amount_cents"],
                "status": pay["status"],
                "occurred_at": pay["created_at"],
            }
        )
    for cn in svc.list_credit_notes(db, ctx):
        history.append(
            {
                "kind": "credit_note",
                "id": cn["credit_note_id"],
                "reference": cn.get("order_number"),
                "description": cn.get("reason") or "Credit note",
                "amount_cents": -(cn.get("amount_cents") or 0),
                "status": cn.get("status"),
                "occurred_at": cn["created_at"],
            }
        )
    history.sort(key=lambda x: str(x.get("occurred_at") or ""), reverse=True)
    return history


def tax_summary(svc: Any, db: Session, ctx: MerchantContext) -> dict[str, Any]:
    invoices = [inv for inv, _ in svc._merchant_invoices(db, ctx)]
    return build_tax_summary(invoices)


def contract_pricing(svc: Any, db: Session, ctx: MerchantContext) -> dict[str, Any]:
    merchant = ctx.merchant
    contract = (
        db.query(MerchantContract)
        .filter(MerchantContract.merchant_id == merchant.id, MerchantContract.is_active.is_(True))
        .order_by(MerchantContract.created_at.desc())
        .first()
    )
    return {
        "has_contract": contract is not None,
        "contract_id": contract.id if contract else None,
        "contract_name": contract.name if contract else None,
        "minimum_monthly_commitment_cents": contract.minimum_monthly_commitment_cents if contract else 0,
        "rules": contract.rules if contract else {},
        "pricing_config": merchant.pricing_config or {},
        "effective_from": contract.effective_from.isoformat() if contract and contract.effective_from else None,
        "effective_to": contract.effective_to.isoformat() if contract and contract.effective_to else None,
    }


def export_invoices_csv(svc: Any, db: Session, ctx: MerchantContext) -> str:
    rows = svc.list_invoices_enriched(db, ctx)
    return rows_to_csv(
        rows,
        [
            "invoice_number",
            "order_number",
            "tracking_number",
            "status",
            "amount_cents",
            "tax_cents",
            "outstanding_cents",
            "currency",
            "payment_terms",
            "due_date",
            "created_at",
        ],
    )


def export_statement_csv(svc: Any, db: Session, ctx: MerchantContext) -> str:
    detail = svc.statement_detail(db, ctx)
    return rows_to_csv(
        detail["line_items"],
        ["type", "date", "reference", "description", "amount_cents", "tax_cents", "status"],
    )


def export_history_csv(svc: Any, db: Session, ctx: MerchantContext) -> str:
    return rows_to_csv(
        svc.billing_history(db, ctx),
        ["kind", "reference", "description", "amount_cents", "status", "occurred_at"],
    )


def merchant_invoices(db: Session, ctx: MerchantContext) -> list[tuple[Invoice, Order | None]]:
    """Per-order invoices (legacy) plus consolidated cycle invoices (order is None)."""
    from sqlalchemy import and_, or_

    return (
        db.query(Invoice, Order)
        .outerjoin(Order, Invoice.order_id == Order.id)
        .filter(
            or_(
                Order.merchant_id == ctx.merchant.id,
                and_(Invoice.billing_kind == "cycle", Invoice.merchant_id == ctx.merchant.id),
            )
        )
        .order_by(Invoice.created_at.desc())
        .limit(500)
        .all()
    )


def merchant_ledger(db: Session, ctx: MerchantContext) -> list[BillingLedgerEntry]:
    order_ids = [r[0] for r in db.query(Order.id).filter(Order.merchant_id == ctx.merchant.id).all()]
    if not order_ids:
        return []
    return (
        db.query(BillingLedgerEntry)
        .filter(BillingLedgerEntry.order_id.in_(order_ids))
        .order_by(BillingLedgerEntry.created_at.desc())
        .limit(200)
        .all()
    )


# ── Account ops adapters (credit hold, health v2) ──────────────────────────


def ar_snapshot(db: Session, merchant: Any) -> Any:
    """Delivery AR for one merchant (same cents as Billing)."""
    from porterchain_api.billing_engine.ar import merchant_ar

    return merchant_ar(db, merchant)


def ar_index(db: Session, merchant_ids: list[str]) -> dict[str, Any]:
    from porterchain_api.billing_engine.ar import merchant_ar_index

    return merchant_ar_index(db, merchant_ids=merchant_ids)


def overdue_invoice_rows(db: Session, merchant: Any, *, now: Any) -> list[dict[str, Any]]:
    """Open delivery invoices past due, oldest first, with days overdue."""
    from porterchain_api.billing_engine.ar import _latest_payment_by_order
    from porterchain_api.billing_engine.merchant_service import (
        effective_payment_terms,
        invoice_due_date,
        invoice_status,
        outstanding_cents,
    )

    def aware(dt: Any) -> Any:
        if dt is None:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=now.tzinfo)

    def row(inv: Any, status: str, terms: Any, kind: str) -> dict[str, Any]:
        due = aware(getattr(inv, "due_at", None)) or aware(invoice_due_date(inv.created_at, terms))
        return {
            "invoice_id": inv.id,
            "order_id": inv.order_id,
            "kind": kind,
            "amount_cents": outstanding_cents(inv, status),
            "due_at": due.isoformat() if due else None,
            "days_overdue": max(0, (now - due).days) if due else 0,
        }

    naive_now = now.replace(tzinfo=None)
    out: list[dict[str, Any]] = []
    # Per-order invoices (one per delivery).
    orders = {
        o.id: o
        for o in db.query(Order).filter(Order.merchant_id == merchant.id, Order.is_sandbox.is_(False)).all()
    }
    if orders:
        payments = _latest_payment_by_order(db, list(orders))
        for inv in db.query(Invoice).filter(Invoice.order_id.in_(list(orders))).all():
            order = orders.get(inv.order_id or "")
            terms = effective_payment_terms(order, merchant)
            status = invoice_status(inv, order, payments.get(inv.order_id or ""), terms=terms, now=naive_now)
            if status == "overdue":
                out.append(row(inv, status, terms, "order"))
    # Billing-cycle invoices (one per period, no single order_id): Interac
    # e-Transfer is matched by hand, so paid_at / voided_at / status close them.
    cycle_terms = getattr(merchant, "payment_terms", None)
    cycle = db.query(Invoice).filter(
        Invoice.merchant_id == merchant.id,
        Invoice.order_id.is_(None),
        Invoice.paid_at.is_(None),
        Invoice.voided_at.is_(None),
        Invoice.status.notin_(("paid", "void", "voided", "cancelled", "draft")),
    )
    for inv in cycle.all():
        status = invoice_status(inv, None, None, terms=cycle_terms, now=naive_now)
        if status == "overdue":
            out.append(row(inv, status, cycle_terms, "cycle"))
    out.sort(key=lambda r: -r["days_overdue"])
    return out
