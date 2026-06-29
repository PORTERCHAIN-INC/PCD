"""Admin dashboard KPIs per MODULE_BREAKDOWN.md."""

from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Claim, Driver, SupportTicket
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.domain.states import OrderState, QuoteState
from porterchain_api.merchant_models import Merchant
from porterchain_api.models import Invoice, Order, Quote


class AdminDashboardService:
    def get_dashboard(self, db: Session) -> dict:
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

        todays_revenue = (
            db.query(func.coalesce(func.sum(Order.amount_cents), 0))
            .filter(Order.created_at >= today_start, Order.state.notin_([OrderState.CANCELLED.value]))
            .scalar()
            or 0
        )
        todays_bookings = db.query(Order).filter(Order.created_at >= today_start).count()
        pending_quotes = db.query(Quote).filter(Quote.state == QuoteState.QUOTE.value).count()
        pending_merchants = (
            db.query(Merchant).filter(Merchant.status == MerchantStatus.PENDING.value).count()
        )
        drivers_online = db.query(Driver).filter(Driver.is_online.is_(True)).count()
        drivers_offline = db.query(Driver).filter(Driver.is_online.is_(False)).count()
        dispatch_queue = db.query(Order).filter(Order.state == OrderState.DISPATCH_READY.value).count()
        in_transit = db.query(Order).filter(
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
        completed_today = db.query(Order).filter(
            Order.state.in_([OrderState.DELIVERED.value, OrderState.POD_COMPLETED.value, OrderState.CLOSED.value]),
            Order.updated_at >= today_start,
        ).count()
        failed_deliveries = db.query(Order).filter(
            Order.state.in_([OrderState.FAILED.value, OrderState.LOST.value, OrderState.DAMAGED.value])
        ).count()
        open_claims = db.query(Claim).filter(Claim.status.in_(["open", "investigating"])).count()
        outstanding_invoices = db.query(func.coalesce(func.sum(Invoice.amount_cents), 0)).scalar() or 0
        open_tickets = db.query(SupportTicket).filter(
            SupportTicket.status.in_(["open", "in_progress", "escalated"])
        ).count()
        fleet_health = round(
            (drivers_online / (drivers_online + drivers_offline) * 100) if (drivers_online + drivers_offline) else 100.0,
            1,
        )

        return {
            "todays_revenue_cents": int(todays_revenue),
            "todays_bookings": todays_bookings,
            "pending_quotes": pending_quotes,
            "pending_merchant_approvals": pending_merchants,
            "drivers_online": drivers_online,
            "drivers_offline": drivers_offline,
            "orders_waiting_dispatch": dispatch_queue,
            "orders_in_transit": in_transit,
            "completed_today": completed_today,
            "failed_deliveries": failed_deliveries,
            "open_claims": open_claims,
            "outstanding_invoices_cents": int(outstanding_invoices),
            "open_support_tickets": open_tickets,
            "fleet_health_percent": fleet_health,
        }
