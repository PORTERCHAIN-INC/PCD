"""Merchant billing — Net terms statements and invoices."""

from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.models import Invoice, Order


class MerchantBillingService:
    def list_invoices(self, db: Session, ctx: MerchantContext) -> list[dict]:
        rows = (
            db.query(Invoice, Order)
            .join(Order, Invoice.order_id == Order.id)
            .filter(Order.merchant_id == ctx.merchant.id)
            .order_by(Invoice.created_at.desc())
            .limit(100)
            .all()
        )
        return [
            {
                "invoice_id": inv.id,
                "invoice_number": inv.invoice_number,
                "order_id": inv.order_id,
                "amount_cents": inv.amount_cents,
                "currency": inv.currency,
                "created_at": inv.created_at,
                "stripe_receipt_url": inv.stripe_receipt_url,
                "pdf_url": inv.pdf_url,
            }
            for inv, _ in rows
        ]

    def outstanding_balance(self, db: Session, ctx: MerchantContext) -> int:
        invoiced_order_ids = (
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
                ~Order.id.in_(db.query(invoiced_order_ids.c.order_id)),
            )
            .scalar()
            or 0
        )
        return int(total)

    def statement_summary(self, db: Session, ctx: MerchantContext) -> dict:
        month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_orders = (
            db.query(func.count(Order.id))
            .filter(Order.merchant_id == ctx.merchant.id, Order.created_at >= month_start)
            .scalar()
            or 0
        )
        monthly_spend = (
            db.query(func.coalesce(func.sum(Order.amount_cents), 0))
            .filter(Order.merchant_id == ctx.merchant.id, Order.created_at >= month_start)
            .scalar()
            or 0
        )
        return {
            "payment_terms": ctx.merchant.payment_terms,
            "outstanding_balance_cents": self.outstanding_balance(db, ctx),
            "monthly_orders": int(monthly_orders),
            "monthly_spend_cents": int(monthly_spend),
        }
