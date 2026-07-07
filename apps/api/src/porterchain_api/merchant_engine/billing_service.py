"""Merchant billing — orchestrates billing_engine for net-terms merchants."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_models import MerchantContract
from porterchain_api.billing_engine.merchant_service import (
    BILLING_CYCLES,
    billing_period_bounds,
    build_tax_summary,
    invoice_status,
    merchant_uses_stripe,
    net_terms_days,
    outstanding_cents,
    rows_to_csv,
    serialize_invoice_row,
)
from porterchain_api.billing_engine.models import BillingLedgerEntry
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.models import Invoice, Order, Payment
from porterchain_api.merchant_engine import reporting_metrics as report_engine


class MerchantBillingService:
    def _merchant_order_ids(self, db: Session, merchant_id: str):
        return db.query(Order.id).filter(Order.merchant_id == merchant_id)

    def _payment_for_order(self, db: Session, order_id: str) -> Payment | None:
        return (
            db.query(Payment)
            .filter(Payment.order_id == order_id)
            .order_by(Payment.created_at.desc())
            .first()
        )

    def overview(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        merchant = ctx.merchant
        period_start, period_end = billing_period_bounds(
            merchant.billing_cycle,
            anchor=merchant.activated_at or merchant.created_at,
        )
        invoices = self._merchant_invoices(db, ctx)
        enriched = self.list_invoices_enriched(db, ctx)
        payments = self.list_payments(db, ctx)
        credit_notes = self.list_credit_notes(db, ctx)
        tax = self.tax_summary(db, ctx)
        contract = self.contract_pricing(db, ctx)

        outstanding_invoices = sum(r["outstanding_cents"] for r in enriched)
        uninvoiced = self._uninvoiced_total(db, ctx)
        credit_notes_cents = self._credit_notes_total(db, ctx)
        outstanding_balance = max(0, outstanding_invoices + uninvoiced - credit_notes_cents)

        summary = self.statement_summary(db, ctx)

        return {
            **summary,
            "credit_limit_cents": merchant.credit_limit_cents,
            "outstanding_balance_cents": outstanding_balance,
            "outstanding_invoices_cents": outstanding_invoices,
            "uninvoiced_orders_cents": uninvoiced,
            "credit_notes_cents": credit_notes_cents,
            "billing_cycles_available": list(BILLING_CYCLES),
            "invoices_due": sum(
                1 for r in enriched if r["status"] in ("sent", "overdue", "pending") and r["outstanding_cents"] > 0
            ),
            "overdue_invoices": sum(1 for r in enriched if r["status"] == "overdue"),
            "invoice_count": len(invoices),
            "payment_count": len(payments),
            "credit_notes_count": len(credit_notes),
            "tax_summary": tax,
            "contract_pricing": contract,
        }

    def statement_summary(self, db: Session, ctx: MerchantContext) -> dict:
        merchant = ctx.merchant
        period_start, period_end = billing_period_bounds(
            merchant.billing_cycle,
            anchor=merchant.activated_at or merchant.created_at,
        )
        monthly_orders = (
            db.query(func.count(Order.id))
            .filter(
                Order.merchant_id == merchant.id,
                Order.created_at >= period_start,
                Order.created_at < period_end,
            )
            .scalar()
            or 0
        )
        monthly_spend = (
            db.query(func.coalesce(func.sum(Order.amount_cents), 0))
            .filter(
                Order.merchant_id == merchant.id,
                Order.created_at >= period_start,
                Order.created_at < period_end,
                Order.state.notin_([OrderState.CANCELLED.value, OrderState.REFUNDED.value]),
            )
            .scalar()
            or 0
        )
        enriched = self.list_invoices_enriched(db, ctx)
        outstanding_invoices = sum(r["outstanding_cents"] for r in enriched)
        uninvoiced = self._uninvoiced_total(db, ctx)
        credit_notes_cents = self._credit_notes_total(db, ctx)

        return {
            "payment_terms": merchant.payment_terms,
            "billing_cycle": merchant.billing_cycle,
            "net_terms_days": net_terms_days(merchant.payment_terms),
            "stripe_enabled": merchant_uses_stripe(merchant),
            "outstanding_balance_cents": max(0, outstanding_invoices + uninvoiced - credit_notes_cents),
            "outstanding_invoices_cents": outstanding_invoices,
            "uninvoiced_orders_cents": uninvoiced,
            "credit_notes_cents": credit_notes_cents,
            "monthly_orders": int(monthly_orders),
            "monthly_spend_cents": int(monthly_spend),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
        }

    def statement_detail(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        merchant = ctx.merchant
        period_start, period_end = billing_period_bounds(
            merchant.billing_cycle,
            anchor=merchant.activated_at or merchant.created_at,
        )
        lines: list[dict[str, Any]] = []

        orders = (
            db.query(Order)
            .filter(
                Order.merchant_id == merchant.id,
                Order.created_at >= period_start,
                Order.created_at < period_end,
                Order.state.notin_([OrderState.CANCELLED.value, OrderState.REFUNDED.value]),
            )
            .order_by(Order.created_at.asc())
            .all()
        )
        for order in orders:
            inv = db.query(Invoice).filter(Invoice.order_id == order.id).first()
            payment = self._payment_for_order(db, order.id)
            lines.append(
                {
                    "type": "order",
                    "date": order.created_at.isoformat() if order.created_at else None,
                    "reference": order.order_number,
                    "tracking_number": order.tracking_number,
                    "description": f"Delivery {order.tracking_number}",
                    "amount_cents": order.amount_cents,
                    "tax_cents": inv.tax_cents if inv else 0,
                    "invoiced": inv is not None,
                    "invoice_number": inv.invoice_number if inv else None,
                    "status": invoice_status(inv, order, payment, terms=merchant.payment_terms)
                    if inv
                    else "uninvoiced",
                }
            )

        for entry in self._merchant_ledger(db, ctx):
            if entry.kind == "credit_note":
                lines.append(
                    {
                        "type": "credit_note",
                        "date": entry.created_at.isoformat() if entry.created_at else None,
                        "reference": entry.id,
                        "description": (entry.metadata_json or {}).get("reason", "Credit note"),
                        "amount_cents": -(entry.amount_cents or 0),
                        "tax_cents": 0,
                    }
                )

        for pay, order in (
            db.query(Payment, Order)
            .join(Order, Payment.order_id == Order.id)
            .filter(
                Order.merchant_id == merchant.id,
                Payment.created_at >= period_start,
                Payment.created_at < period_end,
            )
            .order_by(Payment.created_at.asc())
            .all()
        ):
            lines.append(
                {
                    "type": "payment",
                    "date": pay.created_at.isoformat() if pay.created_at else None,
                    "reference": pay.payment_reference or pay.id,
                    "description": f"Payment ({pay.payment_method or 'net_terms'})",
                    "amount_cents": -pay.amount_cents,
                    "tax_cents": 0,
                }
            )

        lines.sort(key=lambda x: x.get("date") or "")

        merchant_id = merchant.id
        period_start_dt = period_start
        delivery = report_engine.delivery_performance(db, merchant_id, since=period_start_dt)
        invoices = report_engine.invoice_summary(db, merchant_id, since=period_start_dt)
        avg_hours = delivery.get("avg_delivery_hours")

        return {
            **self.statement_summary(db, ctx),
            "line_items": lines,
            "line_items_total_cents": sum(int(l.get("amount_cents") or 0) for l in lines if l["type"] == "order"),
            "delivery_success_percent": delivery["delivery_success_percent"],
            "average_delivery_minutes": int(avg_hours * 60) if avg_hours is not None else None,
            "top_routes": report_engine.top_routes(db, merchant_id, since=period_start_dt),
            "invoice_summary_cents": invoices["invoice_total_cents"],
        }

    def list_invoices(self, db: Session, ctx: MerchantContext) -> list[dict]:
        return self.list_invoices_enriched(db, ctx)

    def list_invoices_enriched(self, db: Session, ctx: MerchantContext) -> list[dict]:
        rows = self._merchant_invoices(db, ctx)
        result: list[dict] = []
        include_stripe = merchant_uses_stripe(ctx.merchant)
        for inv, order in rows:
            payment = self._payment_for_order(db, inv.order_id)
            row = serialize_invoice_row(
                inv,
                order,
                payment,
                terms=ctx.merchant.payment_terms,
                include_stripe=include_stripe,
            )
            result.append(row)
        return result

    def get_invoice_pdf_url(self, db: Session, ctx: MerchantContext, invoice_id: str) -> str | None:
        row = (
            db.query(Invoice, Order)
            .join(Order, Invoice.order_id == Order.id)
            .filter(Invoice.id == invoice_id, Order.merchant_id == ctx.merchant.id)
            .first()
        )
        if not row:
            raise LookupError("invoice_not_found")
        inv, _order = row
        if inv.pdf_url:
            return inv.pdf_url
        if merchant_uses_stripe(ctx.merchant) and inv.stripe_receipt_url:
            return inv.stripe_receipt_url
        return None

    def list_payments(self, db: Session, ctx: MerchantContext) -> list[dict[str, Any]]:
        rows = (
            db.query(Payment, Order)
            .join(Order, Payment.order_id == Order.id)
            .filter(Order.merchant_id == ctx.merchant.id)
            .order_by(Payment.created_at.desc())
            .limit(200)
            .all()
        )
        include_stripe = merchant_uses_stripe(ctx.merchant)
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
                "payment_method": pay.payment_method or ("stripe" if pay.stripe_payment_intent_id else "net_terms"),
                "payment_reference": pay.payment_reference,
                "created_at": pay.created_at.isoformat() if pay.created_at else None,
            }
            if include_stripe and pay.receipt_url:
                item["receipt_url"] = pay.receipt_url
            out.append(item)
        return out

    def list_credit_notes(self, db: Session, ctx: MerchantContext) -> list[dict[str, Any]]:
        order_ids = [r[0] for r in self._merchant_order_ids(db, ctx.merchant.id).all()]
        if not order_ids:
            return []
        entries = (
            db.query(BillingLedgerEntry)
            .filter(
                BillingLedgerEntry.kind == "credit_note",
                BillingLedgerEntry.order_id.in_(order_ids),
            )
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

    def billing_history(self, db: Session, ctx: MerchantContext) -> list[dict[str, Any]]:
        history: list[dict[str, Any]] = []
        for inv_row in self.list_invoices_enriched(db, ctx):
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
        for pay in self.list_payments(db, ctx):
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
        for cn in self.list_credit_notes(db, ctx):
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

    def tax_summary(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        invoices = [inv for inv, _ in self._merchant_invoices(db, ctx)]
        return build_tax_summary(invoices)

    def contract_pricing(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
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

    def export_invoices_csv(self, db: Session, ctx: MerchantContext) -> str:
        rows = self.list_invoices_enriched(db, ctx)
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

    def export_statement_csv(self, db: Session, ctx: MerchantContext) -> str:
        detail = self.statement_detail(db, ctx)
        return rows_to_csv(
            detail["line_items"],
            ["type", "date", "reference", "description", "amount_cents", "tax_cents", "status"],
        )

    def export_history_csv(self, db: Session, ctx: MerchantContext) -> str:
        return rows_to_csv(
            self.billing_history(db, ctx),
            ["kind", "reference", "description", "amount_cents", "status", "occurred_at"],
        )

    def _merchant_invoices(self, db: Session, ctx: MerchantContext) -> list[tuple[Invoice, Order]]:
        return (
            db.query(Invoice, Order)
            .join(Order, Invoice.order_id == Order.id)
            .filter(Order.merchant_id == ctx.merchant.id)
            .order_by(Invoice.created_at.desc())
            .limit(500)
            .all()
        )

    def _merchant_ledger(self, db: Session, ctx: MerchantContext) -> list[BillingLedgerEntry]:
        order_ids = [r[0] for r in self._merchant_order_ids(db, ctx.merchant.id).all()]
        if not order_ids:
            return []
        return (
            db.query(BillingLedgerEntry)
            .filter(BillingLedgerEntry.order_id.in_(order_ids))
            .order_by(BillingLedgerEntry.created_at.desc())
            .limit(200)
            .all()
        )

    def _uninvoiced_total(self, db: Session, ctx: MerchantContext) -> int:
        invoiced_ids = (
            db.query(Invoice.order_id)
            .join(Order, Invoice.order_id == Order.id)
            .filter(Order.merchant_id == ctx.merchant.id)
            .subquery()
        )
        total = (
            db.query(func.coalesce(func.sum(Order.amount_cents), 0))
            .filter(
                Order.merchant_id == ctx.merchant.id,
                Order.state.notin_([OrderState.CANCELLED.value, OrderState.REFUNDED.value]),
                ~Order.id.in_(db.query(invoiced_ids.c.order_id)),
            )
            .scalar()
            or 0
        )
        return int(total)

    def _credit_notes_total(self, db: Session, ctx: MerchantContext) -> int:
        return sum(int(cn.get("amount_cents") or 0) for cn in self.list_credit_notes(db, ctx))

    def outstanding_balance(self, db: Session, ctx: MerchantContext) -> int:
        enriched = self.list_invoices_enriched(db, ctx)
        gross = sum(r["outstanding_cents"] for r in enriched) + self._uninvoiced_total(db, ctx)
        return max(0, gross - self._credit_notes_total(db, ctx))
