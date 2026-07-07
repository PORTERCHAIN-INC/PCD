"""Admin dashboard KPIs and Executive Command Center aggregation (masterrule §3).

Orchestrates existing Application Services — does not duplicate module business logic.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Claim, Driver, SupportTicket
from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.domain.states import OrderState, QuoteState
from porterchain_api.merchant_models import Merchant
from porterchain_api.models import Invoice, Order, Payment, Quote

PORTERCHAIN_VERSION = os.environ.get("PORTERCHAIN_VERSION", "3.1.0")


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

    def get_center(self, db: Session, settings: Settings, *, role: str = "admin") -> dict[str, Any]:
        """Single payload for the Executive Command Center UI."""
        from porterchain_api.admin_engine.booking_draft_admin_service import AdminBookingDraftService
        from porterchain_api.admin_engine.claims_service import AdminClaimsService
        from porterchain_api.admin_engine.control_tower_service import ControlTowerService
        from porterchain_api.admin_engine.orders_service import AdminOrdersService
        from porterchain_api.admin_engine.settings_service import AdminSettingsService
        from porterchain_api.admin_engine.support_service import AdminSupportService
        from porterchain_api.admin_models import Vehicle
        from porterchain_api.models import Customer

        finance_svc = AdminFinanceService()
        ops = ControlTowerService()
        kpis = self.get_dashboard(db)
        ops_stats = ops.stats(db)
        orders = AdminOrdersService().dashboard(db)
        finance = finance_svc.dashboard(db)
        claims = AdminClaimsService().dashboard(db)
        support = AdminSupportService().dashboard(db)
        booking = AdminBookingDraftService().analytics(db)
        trends = finance.get("revenue_trend", []) or {"labels": [], "orders": [], "revenue_cents": []}
        executive = {"orders": orders, "finance": finance}
        smart = {"alerts": ops_stats.get("open_exceptions", 0)}
        merchants_summary = {
            "top_merchants_by_orders": [],
            "top_merchants_by_revenue": [],
        }
        customers = {"new_customers_month": db.query(func.count(Customer.id)).scalar() or 0}
        drivers = {"active_assignments": orders.get("assigned", 0)}
        sla = ops.sla_monitor(db, limit=10)
        activity = ops.live_activity(db, limit=25)
        ai_ops = ops.ai_ops(db)
        health = AdminSettingsService().integration_health(db, settings)

        vehicles_total = db.query(func.count(Vehicle.id)).scalar() or 0
        vehicles_active = int(ops_stats.get("vehicles_active", 0))
        active_merchants = db.query(Merchant).filter(Merchant.status == MerchantStatus.ACTIVE.value).count()

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
            "revenue_forecast_cents": finance.get("revenue_forecast_cents", 0),
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
            "crm": {
                "new_leads": 0,
                "todays_follow_ups": 0,
                "meetings_today": 0,
                "open_deals": 0,
                "won_deals_this_month": 0,
            },
            "booking": booking,
            "merchants": {
                "pending_approval": kpis["pending_merchant_approvals"],
                "active": active_merchants,
                "top_by_orders": merchants_summary.get("top_merchants_by_orders", [])[:5],
                "top_by_revenue": merchants_summary.get("top_merchants_by_revenue", [])[:5],
                "contracts_expiring": 0,
            },
            "customers": customers,
            "drivers": {
                **drivers,
                "online": kpis["drivers_online"],
                "offline": kpis["drivers_offline"],
                "busy": max(kpis["drivers_online"] - int(orders.get("assigned", 0)), 0),
                "available": max(kpis["drivers_online"] - int(orders.get("assigned", 0)), 0),
            },
            "fleet": {
                "vehicles_total": vehicles_total,
                "vehicles_active": vehicles_active,
                "vehicles_available": max(vehicles_total - vehicles_active, 0),
                "utilization_percent": kpis["fleet_health_percent"],
            },
            "trends": trends,
            "executive": executive,
            "activity": activity,
            "system_health": health,
            "smart": smart,
            "pending": {
                "merchant_approvals": kpis["pending_merchant_approvals"],
                "contracts": 0,
                "claims_open": claims.get("open_claims", 0),
                "support_open": support.get("open_tickets", 0),
                "quotes": kpis["pending_quotes"],
                "overdue_tasks": 0,
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
        from porterchain_api.admin_engine.live_map_service import LiveMapService
        from porterchain_api.models import BookingDraft

        q = query.strip()
        if len(q) < 2:
            return []

        hits = LiveMapService().search(db, q, limit=limit)
        like = f"%{q}%"

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
