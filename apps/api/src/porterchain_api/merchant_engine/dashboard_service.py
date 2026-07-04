"""Merchant dashboard aggregates — orchestrates existing Application Services (masterrule §3)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Claim, SupportTicket
from porterchain_api.domain.admin_states import ClaimStatus, TicketStatus
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine.billing_service import MerchantBillingService
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.reports_service import MerchantReportsService
from porterchain_api.merchant_models import MerchantAuditLog
from porterchain_api.models import Invoice, Order, OrderEvent


_AWAITING_PICKUP_STATES = (
    OrderState.BOOKED.value,
    OrderState.DISPATCH_READY.value,
    OrderState.DRIVER_ASSIGNED.value,
    OrderState.DRIVER_ACCEPTED.value,
    OrderState.DRIVER_EN_ROUTE.value,
    OrderState.AT_PICKUP.value,
)

_IN_TRANSIT_STATES = (
    OrderState.PICKED_UP.value,
    OrderState.IN_TRANSIT.value,
    OrderState.AT_DESTINATION.value,
)

_DELIVERED_STATES = (
    OrderState.DELIVERED.value,
    OrderState.POD_COMPLETED.value,
    OrderState.CLOSED.value,
)

_OPEN_CLAIM_STATES = (ClaimStatus.OPEN.value, ClaimStatus.INVESTIGATING.value)

_OPEN_TICKET_STATES = (
    TicketStatus.OPEN.value,
    TicketStatus.IN_PROGRESS.value,
    TicketStatus.ESCALATED.value,
)


class MerchantDashboardService:
    def __init__(self) -> None:
        self._billing = MerchantBillingService()
        self._reports = MerchantReportsService()

    def get_dashboard(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        merchant_id = ctx.merchant.id
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = today_start.replace(day=1)

        base = db.query(Order).filter(Order.merchant_id == merchant_id)
        statement = self._billing.statement_summary(db, ctx)
        reports = self._reports.summary(db, ctx)

        todays_orders = base.filter(Order.created_at >= today_start).count()
        awaiting_pickup = base.filter(Order.state.in_(_AWAITING_PICKUP_STATES)).count()
        in_transit = base.filter(Order.state.in_(_IN_TRANSIT_STATES)).count()
        delivered_today = base.filter(
            Order.state.in_(_DELIVERED_STATES),
            Order.updated_at >= today_start,
        ).count()

        open_claims = (
            db.query(func.count(Claim.id))
            .join(Order, Claim.order_id == Order.id)
            .filter(Order.merchant_id == merchant_id, Claim.status.in_(_OPEN_CLAIM_STATES))
            .scalar()
            or 0
        )
        open_support_tickets = (
            db.query(func.count(SupportTicket.id))
            .filter(SupportTicket.merchant_id == merchant_id, SupportTicket.status.in_(_OPEN_TICKET_STATES))
            .scalar()
            or 0
        )

        invoices_due = (
            db.query(func.count(Order.id))
            .outerjoin(Invoice, Invoice.order_id == Order.id)
            .filter(
                Order.merchant_id == merchant_id,
                Order.state.in_(
                    [
                        OrderState.DELIVERED.value,
                        OrderState.POD_COMPLETED.value,
                        OrderState.INVOICED.value,
                        OrderState.CLOSED.value,
                    ]
                ),
                Invoice.id.is_(None),
            )
            .scalar()
            or 0
        )

        closed_count = base.filter(Order.state == OrderState.CLOSED.value, Order.created_at >= month_start).count()
        total_month = base.filter(Order.created_at >= month_start).count()
        on_time_percent = round((closed_count / total_month * 100) if total_month else 100.0, 1)

        return {
            "todays_orders": todays_orders,
            "awaiting_pickup": awaiting_pickup,
            "pending_dispatch": base.filter(Order.state == OrderState.DISPATCH_READY.value).count(),
            "in_transit": in_transit,
            "delivered_today": delivered_today,
            "monthly_orders": int(statement["monthly_orders"]),
            "monthly_spend_cents": int(statement["monthly_spend_cents"]),
            "outstanding_balance_cents": int(statement["outstanding_balance_cents"]),
            "outstanding_invoices_cents": int(statement["outstanding_balance_cents"]),
            "account_balance_cents": int(statement["outstanding_balance_cents"]),
            "invoices_due": int(invoices_due),
            "open_claims": int(open_claims),
            "open_support_tickets": int(open_support_tickets),
            "on_time_percent": on_time_percent,
            "delivery_success_percent": reports["delivery_success_percent"],
            "payment_terms": ctx.merchant.payment_terms,
            "recent_deliveries": self._recent_deliveries(db, merchant_id),
            "recent_activity": self._recent_activity(db, merchant_id),
            "performance_charts": self._performance_charts(db, merchant_id, today_start),
            "notifications": self._notifications(db, merchant_id),
            "latest_invoice": self._latest_invoice(db, merchant_id),
        }

    def _recent_deliveries(self, db: Session, merchant_id: str, *, limit: int = 8) -> list[dict[str, Any]]:
        rows = (
            db.query(Order)
            .filter(Order.merchant_id == merchant_id, Order.state.in_(_DELIVERED_STATES))
            .order_by(Order.updated_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "order_id": o.id,
                "order_number": o.order_number,
                "tracking_number": o.tracking_number,
                "state": o.state,
                "amount_cents": o.amount_cents,
                "dropoff": o.dropoff.get("formatted") if isinstance(o.dropoff, dict) else None,
                "delivered_at": o.updated_at.isoformat(),
            }
            for o in rows
        ]

    def _recent_activity(self, db: Session, merchant_id: str, *, limit: int = 12) -> list[dict[str, Any]]:
        audit_rows = (
            db.query(MerchantAuditLog)
            .filter(MerchantAuditLog.merchant_id == merchant_id)
            .order_by(MerchantAuditLog.created_at.desc())
            .limit(limit)
            .all()
        )
        event_rows = (
            db.query(OrderEvent)
            .join(Order, OrderEvent.order_id == Order.id)
            .filter(Order.merchant_id == merchant_id)
            .order_by(OrderEvent.occurred_at.desc())
            .limit(limit)
            .all()
        )

        items: list[dict[str, Any]] = []
        for row in audit_rows:
            items.append(
                {
                    "id": row.id,
                    "kind": "audit",
                    "title": row.action.replace(".", " ").replace("_", " ").title(),
                    "detail": row.resource_type,
                    "occurred_at": row.created_at.isoformat(),
                }
            )
        for row in event_rows:
            items.append(
                {
                    "id": row.id,
                    "kind": "order",
                    "title": row.event_type.replace(".", " ").replace("_", " ").title(),
                    "detail": row.to_state or row.from_state,
                    "occurred_at": row.occurred_at.isoformat(),
                }
            )
        items.sort(key=lambda x: x["occurred_at"], reverse=True)
        return items[:limit]

    def _performance_charts(self, db: Session, merchant_id: str, today_start: datetime) -> dict[str, Any]:
        days = 7
        daily_orders: list[dict[str, Any]] = []
        daily_spend: list[dict[str, Any]] = []
        for offset in range(days - 1, -1, -1):
            day = today_start - timedelta(days=offset)
            next_day = day + timedelta(days=1)
            count = (
                db.query(func.count(Order.id))
                .filter(
                    Order.merchant_id == merchant_id,
                    Order.created_at >= day,
                    Order.created_at < next_day,
                )
                .scalar()
                or 0
            )
            spend = (
                db.query(func.coalesce(func.sum(Order.amount_cents), 0))
                .filter(
                    Order.merchant_id == merchant_id,
                    Order.created_at >= day,
                    Order.created_at < next_day,
                )
                .scalar()
                or 0
            )
            label = day.strftime("%a")
            daily_orders.append({"label": label, "value": int(count)})
            daily_spend.append({"label": label, "value": int(spend)})

        month_start = today_start.replace(day=1)
        state_rows = (
            db.query(Order.state, func.count(Order.id))
            .filter(Order.merchant_id == merchant_id, Order.created_at >= month_start)
            .group_by(Order.state)
            .all()
        )
        return {
            "daily_orders": daily_orders,
            "daily_spend_cents": daily_spend,
            "orders_by_state": [{"state": s, "count": int(n)} for s, n in state_rows if s],
        }

    def _notifications(self, db: Session, merchant_id: str, *, limit: int = 10) -> list[dict[str, Any]]:
        try:
            from porterchain_api.notification_engine.models import NotificationRecord

            rows = (
                db.query(NotificationRecord)
                .filter(
                    NotificationRecord.recipient_type == "merchant",
                    NotificationRecord.recipient_id == merchant_id,
                    NotificationRecord.channel == "in_app",
                    NotificationRecord.is_archived.is_(False),
                )
                .order_by(NotificationRecord.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": r.id,
                    "title": r.title,
                    "body": r.body,
                    "category": r.category,
                    "priority": r.priority,
                    "deep_link": r.deep_link,
                    "is_read": r.is_read,
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ]
        except Exception:  # noqa: BLE001
            return []

    def _latest_invoice(self, db: Session, merchant_id: str) -> dict[str, Any] | None:
        row = (
            db.query(Invoice)
            .join(Order, Invoice.order_id == Order.id)
            .filter(Order.merchant_id == merchant_id)
            .order_by(Invoice.created_at.desc())
            .first()
        )
        if not row:
            return None
        return {
            "invoice_id": row.id,
            "invoice_number": row.invoice_number,
            "pdf_url": row.pdf_url,
            "stripe_receipt_url": row.stripe_receipt_url,
        }
