"""Admin dashboard KPIs and Executive Command Center aggregation (masterrule §3).

Orchestrates existing Application Services — does not duplicate module business logic.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Claim, Driver, SupportTicket
from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.domain.states import OrderState, QuoteState
from porterchain_api.merchant_models import Merchant
from porterchain_api.booking_models import Invoice, Order, Payment, Quote

PORTERCHAIN_VERSION = os.environ.get("PORTERCHAIN_VERSION", "3.1.0")


def _chart_trends(db: Session, revenue_trend: list[dict[str, Any]] | dict[str, Any] | None) -> dict[str, list]:
    """Normalize finance revenue_trend rows into admin dashboard chart shape."""
    if isinstance(revenue_trend, dict) and "labels" in revenue_trend:
        return {
            "labels": list(revenue_trend.get("labels") or []),
            "orders": list(revenue_trend.get("orders") or []),
            "revenue_cents": list(revenue_trend.get("revenue_cents") or []),
        }

    labels: list[str] = []
    revenue_cents: list[int] = []
    orders: list[int] = []
    for row in revenue_trend or []:
        day_str = str(row.get("date", ""))
        labels.append(day_str)
        revenue_cents.append(int(row.get("revenue_cents", 0)))
        if day_str:
            day_start = datetime.fromisoformat(day_str).replace(tzinfo=UTC)
            day_end = day_start + timedelta(days=1)
            count = (
                db.query(func.count(Order.id))
                .filter(
                    Order.is_sandbox.is_(False),
                    Order.created_at >= day_start,
                    Order.created_at < day_end,
                )
                .scalar()
                or 0
            )
            orders.append(int(count))
        else:
            orders.append(0)

    return {"labels": labels, "orders": orders, "revenue_cents": revenue_cents}


class AdminDashboardService:
    def get_dashboard(self, db: Session) -> dict:
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        live = Order.is_sandbox.is_(False)

        todays_revenue = (
            db.query(func.coalesce(func.sum(Order.amount_cents), 0))
            .filter(
                live,
                Order.created_at >= today_start,
                Order.state.notin_([OrderState.CANCELLED.value]),
            )
            .scalar()
            or 0
        )
        todays_bookings = db.query(Order).filter(live, Order.created_at >= today_start).count()
        pending_quotes = db.query(Quote).filter(Quote.state == QuoteState.QUOTE.value).count()
        pending_merchants = (
            db.query(Merchant).filter(Merchant.status == MerchantStatus.PENDING.value).count()
        )
        dispatch_queue = (
            db.query(Order).filter(live, Order.state == OrderState.DISPATCH_READY.value).count()
        )
        in_transit = db.query(Order).filter(
            live,
            Order.state.in_(
                [
                    OrderState.PICKED_UP.value,
                    OrderState.IN_TRANSIT.value,
                    OrderState.DRIVER_EN_ROUTE.value,
                    OrderState.AT_PICKUP.value,
                    OrderState.AT_DESTINATION.value,
                ]
            ),
        ).count()
        completed_today = db.query(Order).filter(
            live,
            Order.state.in_([OrderState.DELIVERED.value, OrderState.POD_COMPLETED.value, OrderState.CLOSED.value]),
            Order.updated_at >= today_start,
        ).count()
        failed_deliveries = db.query(Order).filter(
            live,
            Order.state.in_([OrderState.FAILED.value, OrderState.LOST.value, OrderState.DAMAGED.value]),
        ).count()
        open_claims = db.query(Claim).filter(Claim.status.in_(["open", "investigating"])).count()
        outstanding_invoices = db.query(func.coalesce(func.sum(Invoice.amount_cents), 0)).scalar() or 0
        open_tickets = db.query(SupportTicket).filter(
            SupportTicket.status.in_(["open", "in_progress", "escalated"])
        ).count()

        # Derived health — not a constant 100. Penalties for failure / claims pressure.
        fleet_health = round(
            max(0.0, 100.0 - (failed_deliveries * 5) - (open_claims * 2)),
            1,
        )

        return {
            "todays_revenue_cents": int(todays_revenue),
            "todays_bookings": todays_bookings,
            "pending_quotes": pending_quotes,
            "pending_merchant_approvals": pending_merchants,
            "orders_waiting_dispatch": dispatch_queue,
            "orders_in_transit": in_transit,
            "completed_today": completed_today,
            "failed_deliveries": failed_deliveries,
            "open_claims": open_claims,
            "outstanding_invoices_cents": int(outstanding_invoices),
            "open_support_tickets": open_tickets,
            "fleet_health_percent": fleet_health,
        }

    def get_center(self, db: Session, settings: Settings, *, role: str = "admin") -> dict[str, Any]:
        """Single payload for the Executive Command Center UI."""
        from datetime import date, timedelta

        from porterchain_api.admin_engine.booking_draft_admin_service import AdminBookingDraftService
        from porterchain_api.admin_engine.claims_service import AdminClaimsService
        from porterchain_api.admin_engine.control_tower_service import ControlTowerService
        from porterchain_api.admin_engine.finance_service import AdminFinanceService
        from porterchain_api.admin_engine.orders_service import AdminOrdersService
        from porterchain_api.admin_engine.settings_service import AdminSettingsService
        from porterchain_api.admin_engine.support_service import AdminSupportService
        from porterchain_api.admin_models import Vehicle
        from porterchain_api.booking_models import Customer
        from porterchain_api.admin_engine.crm_sales_service import CrmSalesService
        from porterchain_api.crm_models import CrmContract
        from porterchain_api.domain.crm_states import ContractStatus

        finance_svc = AdminFinanceService()
        ops = ControlTowerService()
        kpis = self.get_dashboard(db)
        ops_stats = ops.stats(db)
        orders = AdminOrdersService().dashboard(db)
        finance = finance_svc.dashboard(db)
        claims = AdminClaimsService().dashboard(db)
        support = AdminSupportService().dashboard(db)
        booking = AdminBookingDraftService().analytics(db)
        crm_raw = CrmSalesService().dashboard(db)
        trends = _chart_trends(db, finance.get("revenue_trend"))
        customers = {"new_customers_month": db.query(func.count(Customer.id)).scalar() or 0}
        drivers = {"active_assignments": orders.get("assigned", 0)}
        sla = ops.sla_monitor(db, limit=10)
        activity = ops.live_activity(db, limit=25)
        ai_ops = ops.ai_ops(db)
        health = AdminSettingsService().integration_health(db, settings)

        vehicles_total = db.query(func.count(Vehicle.id)).scalar() or 0
        vehicles_active = int(ops_stats.get("vehicles_active", 0))
        active_merchants = db.query(Merchant).filter(Merchant.status == MerchantStatus.ACTIVE.value).count()

        top_by_revenue = [
            {"name": m.get("name"), "revenue_cents": int(m.get("revenue_cents", 0))}
            for m in (finance.get("top_merchants") or [])[:5]
            if m.get("name")
        ]
        month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        order_rows = (
            db.query(Order.merchant_id, func.count(Order.id))
            .filter(
                Order.is_sandbox.is_(False),
                Order.merchant_id.isnot(None),
                Order.created_at >= month_start,
            )
            .group_by(Order.merchant_id)
            .order_by(func.count(Order.id).desc())
            .limit(5)
            .all()
        )
        merchant_ids = [mid for mid, _ in order_rows if mid]
        merchant_names = {
            m.id: m.company_name
            for m in db.query(Merchant).filter(Merchant.id.in_(merchant_ids)).all()
        } if merchant_ids else {}
        top_by_orders = [
            {
                "id": mid,
                "name": merchant_names.get(mid, mid[:8] if mid else "unknown"),
                "orders": int(cnt),
            }
            for mid, cnt in order_rows
        ]

        today = date.today()
        contracts_expiring = (
            db.query(func.count(CrmContract.id))
            .filter(
                CrmContract.expiry_date.isnot(None),
                CrmContract.expiry_date >= today,
                CrmContract.expiry_date <= today + timedelta(days=30),
                CrmContract.status.notin_(
                    [ContractStatus.EXPIRED.value, ContractStatus.TERMINATED.value]
                ),
            )
            .scalar()
            or 0
        )

        rev_series = list(trends.get("revenue_cents") or [])
        if len(rev_series) >= 2 and rev_series[0]:
            growth_percent = round((rev_series[-1] - rev_series[0]) / rev_series[0] * 100, 1)
        else:
            growth_percent = 0.0

        breached = int(sla.get("breached_count", 0))
        completed = int(ops_stats.get("completed_today", kpis.get("completed_today", 0)))
        sla_denom = max(completed + breached, 1)
        delivery_sla_percent = round(100.0 * (1 - breached / sla_denom), 1)

        forecast_revenue_cents = int(
            finance.get("revenue_forecast_cents")
            or crm_raw.get("monthly_revenue_forecast_cents")
            or 0
        )

        anomalies: list[str] = []
        if breached:
            anomalies.append(f"{breached} SLA breach(es) need attention")
        if int(ops_stats.get("open_exceptions", 0)):
            anomalies.append(f"{ops_stats['open_exceptions']} open exception(s)")
        if int(ops_stats.get("delayed_orders", 0)):
            anomalies.append(f"{ops_stats['delayed_orders']} delayed order(s)")
        for card in (ai_ops.get("risk_orders") or [])[:3]:
            reasons = card.get("reasons") or []
            label = card.get("tracking_number") or card.get("order_number") or card.get("id", "")[:8]
            if reasons:
                anomalies.append(f"{label}: {reasons[0]}")

        crm = {
            "new_leads": int(crm_raw.get("new_leads", 0)),
            "todays_follow_ups": int(crm_raw.get("todays_follow_ups", 0)),
            "meetings_today": int(crm_raw.get("meetings_today", 0)),
            "open_deals": int(crm_raw.get("open_deals", 0)),
            "won_deals_this_month": int(crm_raw.get("won_deals_this_month", 0)),
            "overdue_tasks": int(crm_raw.get("overdue_tasks", 0)),
            "contracts_pending": int(crm_raw.get("contracts_pending", 0)),
            "pipeline_value_cents": int(crm_raw.get("pipeline_value_cents", 0)),
        }

        merged_kpis = {
            **kpis,
            "orders_today": ops_stats.get("orders_today", kpis["todays_bookings"]),
            "revenue_today_cents": ops_stats.get("revenue_today_cents", kpis["todays_revenue_cents"]),
            "orders_in_progress": orders.get("orders_in_progress", ops_stats.get("active_deliveries", 0)),
            "vehicles_active": vehicles_active,
            "vehicles_available": max(vehicles_total - vehicles_active, 0),
            "delayed_orders": ops_stats.get("delayed_orders", 0),
            "high_priority_orders": ops_stats.get("high_priority_orders", 0),
            "late_deliveries": sla.get("breached_count", 0),
            "emergency_orders": ops_stats.get("high_priority_orders", 0),
            "open_exceptions": ops_stats.get("open_exceptions", 0),
            "merchant_growth": active_merchants,
            "customer_growth": customers.get("new_customers_month", 0),
            "avg_delivery_hours": orders.get("avg_delivery_hours", 0),
            "revenue_trend": finance.get("revenue_trend", []),
            "profit_estimate_cents": finance.get("profit_estimate_cents", 0),
            "revenue_forecast_cents": forecast_revenue_cents,
        }

        executive = {
            "orders": orders,
            "finance": finance,
            "growth_percent": growth_percent,
            "delivery_sla_percent": delivery_sla_percent,
            "forecast_revenue_cents": forecast_revenue_cents,
        }
        smart = {
            "alerts": ops_stats.get("open_exceptions", 0),
            "ai_summary": ai_ops.get("recommendation")
            or (
                f"Revenue growth {growth_percent}% · SLA {delivery_sla_percent}% · "
                f"Forecast {forecast_revenue_cents}¢"
            ),
            "anomalies": anomalies,
        }

        return {
            "meta": {
                "generated_at": datetime.now(UTC).isoformat(),
                "environment": settings.app_env,
                "version": PORTERCHAIN_VERSION,
                "company": "Porterchain",
                "role": role,
            },
            "kpis": merged_kpis,
            "operations": {
                **ops_stats,
                "sla_breached": sla.get("breached_count", 0),
                "sla_at_risk": sla.get("at_risk_count", 0),
                "incidents": ops.exceptions(db, limit=8),
                "risk_orders": ai_ops.get("risk_orders", [])[:8],
            },
            "orders": orders,
            "finance": finance,
            "claims": claims,
            "support": support,
            "crm": crm,
            "booking": booking,
            "merchants": {
                "pending_approval": kpis["pending_merchant_approvals"],
                "active": active_merchants,
                "top_by_orders": top_by_orders,
                "top_by_revenue": top_by_revenue,
                "contracts_expiring": int(contracts_expiring),
            },
            "customers": customers,
            "drivers": {
                **drivers,
                # Online/offline/busy/available removed — live driver state is
                # Fleetbase-owned; see the Fleetbase console for live capacity.
            },
            "fleet": {
                "vehicles_total": vehicles_total,
                "vehicles_active": vehicles_active,
                "vehicles_available": max(vehicles_total - vehicles_active, 0),
                "utilization_percent": round(
                    (vehicles_active / vehicles_total * 100) if vehicles_total else 100.0, 1
                ),
            },
            "trends": trends,
            "executive": executive,
            "activity": activity,
            "system_health": health,
            "smart": smart,
            "pending": {
                "merchant_approvals": kpis["pending_merchant_approvals"],
                "contracts": int(crm_raw.get("contracts_pending", 0)),
                "claims_open": claims.get("open_claims", 0),
                "support_open": support.get("open_tickets", 0),
                "quotes": kpis["pending_quotes"],
                "overdue_tasks": int(crm_raw.get("overdue_tasks", 0)),
            },
            "quick_actions": [
                {"id": "booking", "label": "Booking Drafts", "href": "/booking-drafts"},
                {"id": "merchant", "label": "Merchants", "href": "/merchants"},
                {"id": "driver", "label": "Drivers", "href": "/drivers"},
                {"id": "dispatch", "label": "Dispatch", "href": "/operations"},
                {"id": "invoice", "label": "Finance", "href": "/finance"},
                {"id": "claims", "label": "Claims", "href": "/claims"},
                {"id": "support", "label": "Support", "href": "/support"},
            ],
        }

    def global_search(self, db: Session, query: str, *, limit: int = 25) -> list[dict[str, Any]]:
        """Cross-module search for the command center header."""
        from porterchain_api.admin_engine.finance_service import AdminFinanceService
        from porterchain_api.booking_draft_models import BookingDraft

        q = query.strip()
        if len(q) < 2:
            return []

        like = f"%{q}%"
        hits: list[dict[str, Any]] = []

        for o in (
            db.query(Order)
            .filter(or_(Order.tracking_number.ilike(like), Order.order_number.ilike(like), Order.id.ilike(like)))
            .limit(5)
            .all()
        ):
            hits.append(
                {
                    "type": "order",
                    "id": o.id,
                    "label": o.tracking_number or o.order_number or o.id[:8],
                    "subtitle": o.state,
                }
            )

        for d in (
            db.query(Driver)
            .filter(or_(Driver.full_name.ilike(like), Driver.email.ilike(like), Driver.id.ilike(like)))
            .limit(5)
            .all()
        ):
            hits.append({"type": "driver", "id": d.id, "label": d.full_name, "subtitle": d.status})

        for m in (
            db.query(Merchant)
            .filter(or_(Merchant.company_name.ilike(like), Merchant.id.ilike(like)))
            .limit(5)
            .all()
        ):
            hits.append({"type": "merchant", "id": m.id, "label": m.company_name, "subtitle": m.status})

        for t in (
            db.query(SupportTicket)
            .filter(or_(SupportTicket.subject.ilike(like), SupportTicket.id.ilike(like)))
            .limit(5)
            .all()
        ):
            hits.append(
                {
                    "type": "support_ticket",
                    "id": t.id,
                    "label": t.subject,
                    "subtitle": t.status,
                    "href": f"/support/{t.id}",
                }
            )

        for c in (
            db.query(Claim)
            .filter(or_(Claim.id.ilike(like), Claim.order_id.ilike(like)))
            .limit(5)
            .all()
        ):
            hits.append(
                {
                    "type": "claim",
                    "id": c.id,
                    "label": f"Claim {c.id[:8]}",
                    "subtitle": c.status,
                    "href": f"/claims/{c.id}",
                }
            )

        for inv in (
            db.query(Invoice)
            .filter(or_(Invoice.invoice_number.ilike(like), Invoice.id.ilike(like)))
            .limit(5)
            .all()
        ):
            order = db.query(Order).filter(Order.id == inv.order_id).first()
            payment = (
                db.query(Payment).filter(Payment.order_id == inv.order_id).order_by(Payment.created_at.desc()).first()
                if inv.order_id
                else None
            )
            hits.append(
                {
                    "type": "invoice",
                    "id": inv.id,
                    "label": inv.invoice_number or inv.id[:8],
                    "subtitle": AdminFinanceService()._invoice_status(inv, order, payment),
                    "href": "/finance",
                }
            )

        for d in (
            db.query(BookingDraft)
            .filter(BookingDraft.id.ilike(like))
            .limit(5)
            .all()
        ):
            hits.append(
                {
                    "type": "booking_draft",
                    "id": d.id,
                    "label": f"Draft {d.id[:8]}",
                    "subtitle": d.state,
                    "href": f"/booking-drafts/{d.id}",
                }
            )

        type_hrefs = {
            "order": "/orders",
            "driver": "/drivers",
            "merchant": "/merchants",
            "customer": "/merchants",
            "vehicle": "/drivers",
        }
        for h in hits:
            if "href" not in h:
                base = type_hrefs.get(h.get("type", ""), "/dashboard")
                h["href"] = f"{base}/{h['id']}" if h.get("type") in ("order", "driver", "merchant", "booking_draft") else base

        return hits[:limit]
