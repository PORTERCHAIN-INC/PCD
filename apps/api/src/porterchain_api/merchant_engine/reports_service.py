"""Merchant reports per MODULE_BREAKDOWN.md."""

from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.models import Invoice, Order


class MerchantReportsService:
    def summary(self, db: Session, ctx: MerchantContext) -> dict:
        merchant_id = ctx.merchant.id
        month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        base = db.query(Order).filter(Order.merchant_id == merchant_id, Order.created_at >= month_start)
        monthly_orders = base.count()
        monthly_spend = (
            db.query(func.coalesce(func.sum(Order.amount_cents), 0))
            .filter(Order.merchant_id == merchant_id, Order.created_at >= month_start)
            .scalar()
            or 0
        )

        delivered = base.filter(
            Order.state.in_([OrderState.DELIVERED.value, OrderState.POD_COMPLETED.value, OrderState.CLOSED.value])
        ).count()
        delivery_success = round((delivered / monthly_orders * 100) if monthly_orders else 100.0, 1)

        routes: dict[str, int] = {}
        for order in base.limit(500).all():
            key = f"{order.pickup.get('formatted', '?')} → {order.dropoff.get('formatted', '?')}"
            routes[key] = routes.get(key, 0) + 1
        top_routes = sorted(
            [{"route": k, "count": v} for k, v in routes.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:10]

        invoice_total = (
            db.query(func.coalesce(func.sum(Invoice.amount_cents), 0))
            .join(Order, Invoice.order_id == Order.id)
            .filter(Order.merchant_id == merchant_id, Invoice.created_at >= month_start)
            .scalar()
            or 0
        )

        return {
            "monthly_orders": monthly_orders,
            "monthly_spend_cents": int(monthly_spend),
            "delivery_success_percent": delivery_success,
            "average_delivery_minutes": None,
            "top_routes": top_routes,
            "invoice_summary_cents": int(invoice_total),
        }
