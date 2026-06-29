"""Operational and financial reports."""

from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Claim, Driver
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_models import Merchant
from porterchain_api.models import Order


class AdminReportsService:
    def summary(self, db: Session) -> dict:
        month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        orders_month = db.query(Order).filter(Order.created_at >= month_start).count()
        revenue = (
            db.query(func.coalesce(func.sum(Order.amount_cents), 0))
            .filter(Order.created_at >= month_start)
            .scalar()
            or 0
        )
        cancelled = db.query(Order).filter(
            Order.created_at >= month_start, Order.state == OrderState.CANCELLED.value
        ).count()
        cancellation_rate = round((cancelled / orders_month * 100) if orders_month else 0.0, 1)
        delivered = db.query(Order).filter(
            Order.created_at >= month_start,
            Order.state.in_([OrderState.CLOSED.value, OrderState.POD_COMPLETED.value]),
        ).count()
        sla = round((delivered / orders_month * 100) if orders_month else 100.0, 1)
        claims = db.query(Claim).filter(Claim.created_at >= month_start).count()
        claim_rate = round((claims / orders_month * 100) if orders_month else 0.0, 1)
        active_merchants = db.query(Merchant).filter(Merchant.status == MerchantStatus.ACTIVE.value).count()
        active_drivers = db.query(Driver).filter(Driver.status == "APPROVED").count()
        return {
            "monthly_orders": orders_month,
            "monthly_revenue_cents": int(revenue),
            "active_merchants": active_merchants,
            "active_drivers": active_drivers,
            "delivery_sla_percent": sla,
            "cancellation_rate_percent": cancellation_rate,
            "claim_rate_percent": claim_rate,
        }
