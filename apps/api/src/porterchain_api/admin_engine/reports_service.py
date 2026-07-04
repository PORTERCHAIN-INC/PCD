"""Enterprise Reports & BI Center — aggregates existing module analytics (masterrule §3).

All domain metrics are sourced from existing Application Services. This service
orchestrates and shapes data for the admin Reports Center — it does not
duplicate order, finance, claims, or support business rules.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_engine.booking_draft_admin_service import AdminBookingDraftService
from porterchain_api.admin_engine.claims_service import AdminClaimsService
from porterchain_api.admin_engine.crm_sales_service import CrmSalesService
from porterchain_api.admin_engine.dashboard_service import AdminDashboardService
from porterchain_api.admin_engine.finance_service import AdminFinanceService
from porterchain_api.admin_engine.orders_service import AdminOrdersService
from porterchain_api.admin_engine.pricing_service import AdminPricingService
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_engine.support_service import AdminSupportService
from porterchain_api.admin_models import Claim, Driver, SupportTicket, SystemConfig
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_models import Merchant
from porterchain_api.models import Customer, Order, Payment, Quote


REPORT_CATEGORIES: list[dict[str, str]] = [
    {"id": "executive", "label": "Executive Reports", "module": "center"},
    {"id": "operations", "label": "Operations Reports", "module": "orders"},
    {"id": "orders", "label": "Orders Reports", "module": "orders"},
    {"id": "booking", "label": "Booking Reports", "module": "booking"},
    {"id": "booking_drafts", "label": "Booking Draft Reports", "module": "booking"},
    {"id": "merchants", "label": "Merchant Reports", "module": "orders"},
    {"id": "customers", "label": "Customer Reports", "module": "orders"},
    {"id": "drivers", "label": "Driver Reports", "module": "orders"},
    {"id": "fleet", "label": "Fleet Reports", "module": "operations"},
    {"id": "finance", "label": "Finance Reports", "module": "finance"},
    {"id": "revenue", "label": "Revenue Reports", "module": "finance"},
    {"id": "profit", "label": "Profit Reports", "module": "finance"},
    {"id": "invoices", "label": "Invoice Reports", "module": "finance"},
    {"id": "payments", "label": "Payment Reports", "module": "finance"},
    {"id": "refunds", "label": "Refund Reports", "module": "finance"},
    {"id": "claims", "label": "Claims Reports", "module": "claims"},
    {"id": "support", "label": "Support Reports", "module": "support"},
    {"id": "crm", "label": "CRM Reports", "module": "crm"},
    {"id": "pricing", "label": "Pricing Reports", "module": "pricing"},
    {"id": "delivery", "label": "Delivery Performance", "module": "orders"},
    {"id": "compliance", "label": "Compliance Reports", "module": "claims"},
    {"id": "audit", "label": "Audit Reports", "module": "center"},
    {"id": "system", "label": "System Reports", "module": "center"},
]

BUILDER_DATASETS: list[dict[str, Any]] = [
    {
        "id": "orders",
        "label": "Orders",
        "fields": ["state", "merchant_id", "amount_cents", "created_at"],
        "group_by": ["state", "merchant_id"],
        "metrics": ["count", "sum_amount"],
    },
    {
        "id": "payments",
        "label": "Payments",
        "fields": ["status", "amount_cents", "created_at"],
        "group_by": ["status"],
        "metrics": ["count", "sum_amount"],
    },
    {
        "id": "claims",
        "label": "Claims",
        "fields": ["claim_type", "status", "created_at"],
        "group_by": ["claim_type", "status"],
        "metrics": ["count"],
    },
    {
        "id": "support_tickets",
        "label": "Support Tickets",
        "fields": ["category", "status", "priority", "created_at"],
        "group_by": ["category", "status", "priority"],
        "metrics": ["count"],
    },
]

ROLE_DASHBOARDS: dict[str, list[str]] = {
    "ceo": ["executive", "revenue", "operations", "delivery"],
    "operations": ["operations", "orders", "fleet", "delivery"],
    "finance": ["finance", "revenue", "profit", "invoices", "payments"],
    "support": ["support", "customers"],
    "sales": ["crm", "merchants", "pricing"],
}


class AdminReportsService:
    def __init__(self) -> None:
        self._dashboard = AdminDashboardService()
        self._orders = AdminOrdersService()
        self._claims = AdminClaimsService()
        self._finance = AdminFinanceService()
        self._support = AdminSupportService()
        self._pricing = AdminPricingService()
        self._booking_drafts = AdminBookingDraftService()
        self._crm = CrmSalesService()

    def _now(self) -> datetime:
        return datetime.now(UTC)

    def _month_start(self, dt: datetime | None = None) -> datetime:
        ref = dt or self._now()
        return ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def summary(self, db: Session) -> dict[str, Any]:
        month_start = self._month_start()
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
            Order.state.in_([OrderState.CLOSED.value, OrderState.POD_COMPLETED.value, OrderState.DELIVERED.value]),
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

    def module_bundle(self, db: Session) -> dict[str, Any]:
        """Aggregate reports from all existing module services."""
        return {
            "orders": self._orders.reports(db),
            "orders_dashboard": self._orders.dashboard(db),
            "claims": self._claims.reports(db),
            "finance": self._finance.reports(db),
            "finance_dashboard": self._finance.dashboard(db),
            "support": self._support.reports(db),
            "pricing": self._pricing.reports(db),
            "booking_drafts": self._booking_drafts.analytics(db),
            "crm": self._crm.reports(db),
            "operations_dashboard": self._dashboard.get_dashboard(db),
        }

    def monthly_trends(self, db: Session, months: int = 12) -> dict[str, Any]:
        now = self._now()
        labels: list[str] = []
        orders_series: list[int] = []
        revenue_series: list[int] = []
        starts: list[datetime] = []
        for i in range(months - 1, -1, -1):
            year = now.year
            month = now.month - i
            while month <= 0:
                month += 12
                year -= 1
            starts.append(datetime(year, month, 1, tzinfo=UTC))
        for idx, start in enumerate(starts):
            end = starts[idx + 1] if idx + 1 < len(starts) else self._month_start(now) + timedelta(days=32)
            if idx + 1 < len(starts):
                end = starts[idx + 1]
            else:
                end = now + timedelta(days=1)
            labels.append(start.strftime("%Y-%m"))
            cnt = (
                db.query(func.count(Order.id))
                .filter(Order.created_at >= start, Order.created_at < end)
                .scalar()
                or 0
            )
            rev = (
                db.query(func.coalesce(func.sum(Order.amount_cents), 0))
                .filter(
                    Order.created_at >= start,
                    Order.created_at < end,
                    Order.state.notin_([OrderState.CANCELLED.value, OrderState.REFUNDED.value]),
                )
                .scalar()
                or 0
            )
            orders_series.append(int(cnt))
            revenue_series.append(int(rev))
        return {
            "labels": labels,
            "orders": orders_series,
            "revenue_cents": revenue_series,
        }

    def delivery_performance(self, db: Session) -> dict[str, Any]:
        dash = self._orders.dashboard(db)
        orders_rep = self._orders.reports(db)
        month_start = self._month_start()
        total = db.query(func.count(Order.id)).filter(Order.created_at >= month_start).scalar() or 0
        on_time = db.query(func.count(Order.id)).filter(
            Order.created_at >= month_start,
            Order.state.in_([OrderState.DELIVERED.value, OrderState.POD_COMPLETED.value, OrderState.CLOSED.value]),
        ).scalar() or 0
        failed = int(orders_rep.get("failed_deliveries", 0))
        returns = int(orders_rep.get("returns", 0))
        return {
            "avg_pickup_hours": dash.get("avg_pickup_hours", 0),
            "avg_delivery_hours": dash.get("avg_delivery_hours", orders_rep.get("avg_delivery_hours", 0)),
            "sla_percent": dash.get("avg_sla_percent", 0),
            "on_time_percent": round((on_time / total * 100) if total else 0, 1),
            "delay_percent": round((failed / total * 100) if total else 0, 1),
            "failed_percent": round((failed / total * 100) if total else 0, 1),
            "return_percent": round((returns / total * 100) if total else 0, 1),
            "delivered_today": dash.get("delivered", 0),
            "in_progress": dash.get("orders_in_progress", 0),
        }

    def executive(self, db: Session) -> dict[str, Any]:
        summary = self.summary(db)
        finance = self._finance.reports(db)
        orders = self._orders.reports(db)
        trends = self.monthly_trends(db, 6)
        support = self._support.reports(db)
        rev_series = trends["revenue_cents"]
        growth = 0.0
        if len(rev_series) >= 2 and rev_series[-2]:
            growth = round((rev_series[-1] - rev_series[-2]) / rev_series[-2] * 100, 1)
        forecast_cents = int(rev_series[-1] * 1.05) if rev_series else 0
        aov = (
            round(summary["monthly_revenue_cents"] / summary["monthly_orders"])
            if summary["monthly_orders"]
            else 0
        )
        return {
            "revenue_cents": summary["monthly_revenue_cents"],
            "profit_estimate_cents": finance.get("profit_estimate_cents", 0),
            "growth_percent": growth,
            "orders": summary["monthly_orders"],
            "average_order_value_cents": aov,
            "top_merchants": orders.get("top_merchants", [])[:10],
            "top_drivers": orders.get("top_drivers", [])[:10],
            "delivery_sla_percent": summary["delivery_sla_percent"],
            "customer_satisfaction": support.get("customer_satisfaction", 0),
            "monthly_comparison": {
                "labels": trends["labels"][-2:],
                "revenue_cents": rev_series[-2:],
                "orders": trends["orders"][-2:],
            },
            "yearly_comparison": self.monthly_trends(db, 12),
            "forecast_revenue_cents": forecast_cents,
        }

    def operations(self, db: Session) -> dict[str, Any]:
        orders_dash = self._orders.dashboard(db)
        orders_rep = self._orders.reports(db)
        ops = self._dashboard.get_dashboard(db)
        online = ops.get("drivers_online", 0)
        offline = ops.get("drivers_offline", 0)
        driver_util = round(online / (online + offline) * 100, 1) if (online + offline) else 0
        return {
            "orders_created": orders_rep.get("monthly_orders", 0),
            "orders_completed": orders_dash.get("delivered", 0),
            "orders_cancelled": orders_dash.get("failed", 0),
            "orders_returned": orders_rep.get("returns", 0),
            "dispatch_queue": ops.get("orders_waiting_dispatch", 0),
            "in_transit": ops.get("orders_in_transit", 0),
            "avg_pickup_hours": orders_dash.get("avg_pickup_hours", 0),
            "avg_delivery_hours": orders_rep.get("avg_delivery_hours", 0),
            "late_deliveries": orders_rep.get("failed_deliveries", 0),
            "driver_utilization_percent": driver_util,
            "vehicle_utilization_percent": ops.get("fleet_health_percent", 0),
            "fleet_capacity_orders": ops.get("orders_in_transit", 0),
        }

    def category_report(self, db: Session, category_id: str) -> dict[str, Any]:
        mapping: dict[str, Any] = {
            "executive": self.executive,
            "operations": self.operations,
            "orders": lambda d: self._orders.reports(d),
            "booking": lambda d: self._booking_drafts.analytics(d),
            "booking_drafts": lambda d: self._booking_drafts.analytics(d),
            "merchants": self._merchant_report,
            "customers": self._customer_report,
            "drivers": self._driver_report,
            "fleet": self.operations,
            "finance": lambda d: self._finance.reports(d),
            "revenue": lambda d: self._finance.reports(d),
            "profit": lambda d: self._finance.reports(d),
            "invoices": lambda d: self._finance.dashboard(d),
            "payments": lambda d: self._finance.reports(d),
            "refunds": lambda d: {"refund_analysis_cents": self._finance.reports(d).get("refund_analysis_cents", 0)},
            "claims": lambda d: self._claims.reports(d),
            "support": lambda d: self._support.reports(d),
            "crm": lambda d: self._crm.reports(d),
            "pricing": lambda d: self._pricing.reports(d),
            "delivery": self.delivery_performance,
            "compliance": lambda d: self._claims.reports(d),
            "audit": self._audit_summary,
            "system": lambda d: self._dashboard.get_dashboard(d),
        }
        fn = mapping.get(category_id)
        if not fn:
            return {"error": "unknown_category", "category_id": category_id}
        return fn(db)

    def _merchant_report(self, db: Session) -> dict[str, Any]:
        orders = self._orders.reports(db)
        finance = self._finance.reports(db)
        support = self._support.reports(db)
        return {
            "top_merchants_by_orders": orders.get("top_merchants", []),
            "top_merchants_by_revenue": finance.get("top_merchants", []),
            "support_by_merchant": support.get("by_merchant", {}),
            "claims_by_merchant": self._claims.reports(db).get("by_merchant", {}),
        }

    def _customer_report(self, db: Session) -> dict[str, Any]:
        month_start = self._month_start()
        customers = db.query(Customer).all()
        new_this_month = db.query(func.count(Customer.id)).filter(Customer.created_at >= month_start).scalar() or 0
        repeat = 0
        for c in customers:
            cnt = db.query(func.count(Order.id)).filter(Order.customer_id == c.id).scalar() or 0
            if cnt > 1:
                repeat += 1
        return {
            "total_customers": len(customers),
            "new_customers_month": int(new_this_month),
            "repeat_customers": repeat,
            "support_tickets": self._support.reports(db).get("by_type", {}),
        }

    def _driver_report(self, db: Session) -> dict[str, Any]:
        orders = self._orders.reports(db)
        claims = self._claims.reports(db)
        return {
            "top_drivers": orders.get("top_drivers", []),
            "claims_by_driver": claims.get("by_driver", {}),
            "active_drivers": self.summary(db)["active_drivers"],
        }

    def _audit_summary(self, db: Session) -> dict[str, Any]:
        from porterchain_api.admin_models import AdminAuditLog

        month_start = self._month_start()
        logs = (
            db.query(AdminAuditLog)
            .filter(AdminAuditLog.created_at >= month_start)
            .order_by(AdminAuditLog.created_at.desc())
            .limit(50)
            .all()
        )
        by_action: dict[str, int] = {}
        for log in logs:
            by_action[log.action] = by_action.get(log.action, 0) + 1
        return {
            "recent_count": len(logs),
            "by_action": by_action,
            "recent": [
                {
                    "action": l.action,
                    "resource_type": l.resource_type,
                    "created_at": l.created_at.isoformat() if l.created_at else None,
                }
                for l in logs[:20]
            ],
        }

    def center(self, db: Session, *, role: str = "admin") -> dict[str, Any]:
        role_map = {
            "super_admin": "ceo",
            "admin": "ceo",
            "dispatcher": "operations",
            "fleet_manager": "operations",
            "finance": "finance",
            "support": "support",
            "support_lead": "support",
            "sales": "sales",
            "sales_manager": "sales",
        }
        role_key = role_map.get(role, "ceo")
        return {
            "summary": self.summary(db),
            "executive": self.executive(db),
            "operations": self.operations(db),
            "delivery_performance": self.delivery_performance(db),
            "trends": self.monthly_trends(db),
            "modules": self.module_bundle(db),
            "smart": self.smart_insights(db),
            "categories": REPORT_CATEGORIES,
            "role_dashboards": ROLE_DASHBOARDS.get(role_key, ROLE_DASHBOARDS["ceo"]),
        }

    def smart_insights(self, db: Session) -> dict[str, Any]:
        trends = self.monthly_trends(db, 6)
        rev = trends["revenue_cents"]
        anomalies: list[str] = []
        if len(rev) >= 2 and rev[-2] and rev[-1] < rev[-2] * 0.8:
            anomalies.append("Revenue dropped more than 20% vs prior month")
        orders = trends["orders"]
        if len(orders) >= 2 and orders[-2] and orders[-1] > orders[-2] * 1.5:
            anomalies.append("Order volume spike detected")
        direction = "stable"
        if len(rev) >= 3:
            if rev[-1] > rev[-3]:
                direction = "up"
            elif rev[-1] < rev[-3]:
                direction = "down"
        summary = self.summary(db)
        ai_summary = (
            f"This month: {summary['monthly_orders']} orders, "
            f"${summary['monthly_revenue_cents'] / 100:,.0f} revenue, "
            f"{summary['delivery_sla_percent']}% delivery SLA."
        )
        if anomalies:
            ai_summary += " " + " ".join(anomalies)
        forecast = self.executive(db)["forecast_revenue_cents"]
        return {
            "ai_summary": ai_summary,
            "trend_direction": direction,
            "anomalies": anomalies,
            "forecast_revenue_cents": forecast,
        }

    def builder_datasets(self) -> list[dict[str, Any]]:
        return BUILDER_DATASETS

    def builder_preview(
        self,
        db: Session,
        *,
        dataset: str,
        group_by: str,
        metric: str = "count",
    ) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        if dataset == "orders":
            q = db.query(Order)
            for o in q.limit(5000).all():
                key = str(getattr(o, group_by, "unknown"))
                rows.append({"key": key, "amount_cents": o.amount_cents})
        elif dataset == "payments":
            for p in db.query(Payment).limit(5000).all():
                key = str(getattr(p, group_by, "unknown"))
                rows.append({"key": key, "amount_cents": p.amount_cents})
        elif dataset == "claims":
            for c in db.query(Claim).limit(5000).all():
                key = str(getattr(c, group_by, "unknown"))
                rows.append({"key": key, "amount_cents": 0})
        elif dataset == "support_tickets":
            for t in db.query(SupportTicket).limit(5000).all():
                key = str(getattr(t, group_by, "unknown"))
                rows.append({"key": key, "amount_cents": 0})
        else:
            return {"error": "unknown_dataset", "dataset": dataset}
        agg: dict[str, dict[str, float]] = {}
        for r in rows:
            k = r["key"]
            if k not in agg:
                agg[k] = {"count": 0, "sum_amount": 0}
            agg[k]["count"] += 1
            agg[k]["sum_amount"] += r.get("amount_cents", 0)
        series = [
            {
                "label": k,
                "count": int(v["count"]),
                "sum_amount_cents": int(v["sum_amount"]),
                "value": int(v["count"] if metric == "count" else v["sum_amount"]),
            }
            for k, v in sorted(agg.items(), key=lambda x: -x[1]["count"])[:20]
        ]
        return {"dataset": dataset, "group_by": group_by, "metric": metric, "series": series}

    def _config_list(self, db: Session, key: str) -> list[dict[str, Any]]:
        row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if row and isinstance(row.value, dict):
            return list(row.value.get("items") or [])
        if row and isinstance(row.value, list):
            return list(row.value)
        return []

    def _save_config_list(self, db: Session, key: str, items: list[dict[str, Any]]) -> None:
        row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        payload = {"items": items}
        if not row:
            db.add(SystemConfig(key=key, value=payload))
        else:
            row.value = payload

    def list_saved_reports(self, db: Session) -> list[dict[str, Any]]:
        return self._config_list(db, "reports_center_saved")

    def save_report(
        self,
        db: Session,
        ctx: AdminContext,
        *,
        name: str,
        category_id: str,
        chart_type: str = "bar",
        filters: dict[str, Any] | None = None,
        pinned: bool = False,
    ) -> dict[str, Any]:
        items = self.list_saved_reports(db)
        report = {
            "id": str(uuid.uuid4()),
            "name": name,
            "category_id": category_id,
            "chart_type": chart_type,
            "filters": filters or {},
            "pinned": pinned,
            "favorite": False,
            "created_at": self._now().isoformat(),
            "created_by": ctx.user.id,
        }
        items.append(report)
        self._save_config_list(db, "reports_center_saved", items)
        log_admin_audit(
            db,
            ctx,
            action="reports.saved.create",
            resource_type="report",
            resource_id=report["id"],
            payload={"name": name},
        )
        db.commit()
        return report

    def delete_saved_report(self, db: Session, ctx: AdminContext, report_id: str) -> bool:
        items = [r for r in self.list_saved_reports(db) if r.get("id") != report_id]
        self._save_config_list(db, "reports_center_saved", items)
        log_admin_audit(db, ctx, action="reports.saved.delete", resource_type="report", resource_id=report_id)
        db.commit()
        return True

    def list_scheduled_reports(self, db: Session) -> list[dict[str, Any]]:
        return self._config_list(db, "reports_center_scheduled")

    def save_scheduled_report(
        self,
        db: Session,
        ctx: AdminContext,
        *,
        name: str,
        category_id: str,
        schedule: str,
        email: str,
    ) -> dict[str, Any]:
        items = self.list_scheduled_reports(db)
        job = {
            "id": str(uuid.uuid4()),
            "name": name,
            "category_id": category_id,
            "schedule": schedule,
            "email": email,
            "active": True,
            "created_at": self._now().isoformat(),
        }
        items.append(job)
        self._save_config_list(db, "reports_center_scheduled", items)
        log_admin_audit(
            db,
            ctx,
            action="reports.scheduled.create",
            resource_type="scheduled_report",
            resource_id=job["id"],
        )
        db.commit()
        return job

    def log_export(self, db: Session, ctx: AdminContext, *, report_id: str, format: str) -> None:
        log_admin_audit(
            db,
            ctx,
            action="reports.export",
            resource_type="report",
            resource_id=report_id,
            payload={"format": format},
        )
        db.commit()
