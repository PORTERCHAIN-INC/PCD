"""Merchant dashboard aggregates."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.domain.states import OrderState
from porterchain_api.models import Invoice, Order
from porterchain_api.merchant_engine.rbac import MerchantContext


class MerchantDashboardService:
    def get_dashboard(self, db: Session, ctx: MerchantContext) -> dict:
        merchant_id = ctx.merchant.id
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = today_start.replace(day=1)

        base = db.query(Order).filter(Order.merchant_id == merchant_id)

        todays_orders = base.filter(Order.created_at >= today_start).count()
        in_transit = base.filter(
            Order.state.in_(
                [
                    OrderState.PICKED_UP.value,
                    OrderState.IN_TRANSIT.value,
                    OrderState.DRIVER_EN_ROUTE.value,
                    OrderState.AT_PICKUP.value,
                    OrderState.AT_DESTINATION.value,
                ]
            )
        ).count()
        delivered_today = base.filter(
            Order.state.in_([OrderState.DELIVERED.value, OrderState.POD_COMPLETED.value, OrderState.CLOSED.value]),
            Order.updated_at >= today_start,
        ).count()
        pending_dispatch = base.filter(Order.state == OrderState.DISPATCH_READY.value).count()

        monthly_spend = (
            db.query(func.coalesce(func.sum(Order.amount_cents), 0))
            .filter(Order.merchant_id == merchant_id, Order.created_at >= month_start)
            .scalar()
            or 0
        )

        outstanding = (
            db.query(func.coalesce(func.sum(Invoice.amount_cents), 0))
            .filter(Invoice.customer_id.is_(None))
            .join(Order, Invoice.order_id == Order.id)
            .filter(Order.merchant_id == merchant_id)
            .scalar()
            or 0
        )

        closed_count = base.filter(Order.state == OrderState.CLOSED.value, Order.created_at >= month_start).count()
        total_month = base.filter(Order.created_at >= month_start).count()
        on_time = round((closed_count / total_month * 100) if total_month else 100.0, 1)

        return {
            "todays_orders": todays_orders,
            "in_transit": in_transit,
            "delivered_today": delivered_today,
            "pending_dispatch": pending_dispatch,
            "outstanding_invoices_cents": int(outstanding),
            "account_balance_cents": int(outstanding),
            "monthly_spend_cents": int(monthly_spend),
            "on_time_percent": on_time,
            "notifications": [],
        }
