"""Merchant reports — order and billing aggregates (masterrule §3)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.merchant_engine.billing_service import MerchantBillingService
from porterchain_api.merchant_engine.orders_service import MerchantOrdersService
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine import reporting_metrics as report_engine


class MerchantReportsService:
    def __init__(self) -> None:
        self._orders = MerchantOrdersService()
        self._billing = MerchantBillingService()

    def summary(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        """Backward-compatible summary endpoint."""
        exec_data = self.executive(db, ctx)
        return {
            "monthly_orders": exec_data["monthly_orders"],
            "monthly_spend_cents": exec_data["monthly_spend_cents"],
            "delivery_success_percent": exec_data["delivery_success_percent"],
            "average_delivery_minutes": int(exec_data["avg_delivery_hours"] * 60)
            if exec_data.get("avg_delivery_hours")
            else None,
            "top_routes": exec_data.get("top_routes", []),
            "invoice_summary_cents": exec_data.get("invoice_summary_cents", 0),
        }

    def executive(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        merchant_id = ctx.merchant.id
        since = report_engine.month_start()
        ops = self._orders.orders_dashboard(db, ctx)
        delivery = report_engine.delivery_performance(db, merchant_id, since=since)
        trends = report_engine.monthly_trends(db, merchant_id, 6)
        daily = report_engine.daily_volume(db, merchant_id, 7)
        invoices = report_engine.invoice_summary(db, merchant_id, since=since)
        claims = report_engine.claims_summary(db, merchant_id, since=since)

        monthly_orders = trends["orders"][-1] if trends["orders"] else 0
        monthly_spend = trends["spend_cents"][-1] if trends["spend_cents"] else 0
        growth = 0.0
        if len(trends["spend_cents"]) >= 2 and trends["spend_cents"][-2]:
            growth = round(
                (trends["spend_cents"][-1] - trends["spend_cents"][-2]) / trends["spend_cents"][-2] * 100,
                1,
            )

        return {
            "monthly_orders": monthly_orders,
            "monthly_spend_cents": monthly_spend,
            "growth_percent": growth,
            "orders_in_progress": ops.get("orders_in_progress", 0),
            "delivered_today": ops.get("delivered", 0),  # today's delivered count
            "failed_deliveries": delivery["failed_deliveries"],
            "open_claims": claims["open_claims"],
            "on_time_percent": delivery["on_time_percent"],
            "delivery_success_percent": delivery["delivery_success_percent"],
            "sla_percent": delivery["sla_percent"],
            "avg_delivery_hours": delivery["avg_delivery_hours"],
            "avg_pickup_hours": delivery["avg_pickup_hours"],
            "invoice_summary_cents": invoices["invoice_total_cents"],
            "top_routes": report_engine.top_routes(db, merchant_id, since=since),
            "top_destinations": report_engine.top_destinations(db, merchant_id, since=since),
            "charts": {
                "monthly_trends": trends,
                **daily,
            },
            "kpis": [
                {"label": "Monthly orders", "value": monthly_orders, "format": "number"},
                {"label": "Monthly spend", "value": monthly_spend, "format": "currency"},
                {"label": "On-time %", "value": delivery["on_time_percent"], "format": "percent"},
                {"label": "SLA %", "value": delivery["sla_percent"], "format": "percent"},
                {"label": "Failed deliveries", "value": delivery["failed_deliveries"], "format": "number"},
                {"label": "Open claims", "value": claims["open_claims"], "format": "number"},
            ],
        }

    def delivery_performance(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        return report_engine.delivery_performance(db, ctx.merchant.id)

    def order_volume(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        merchant_id = ctx.merchant.id
        return {
            "monthly_trends": report_engine.monthly_trends(db, merchant_id, 6),
            **report_engine.daily_volume(db, merchant_id, 7),
            "top_routes": report_engine.top_routes(db, merchant_id),
        }

    def invoice_reports(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        since = report_engine.month_start()
        summary = report_engine.invoice_summary(db, ctx.merchant.id, since=since)
        invoices = self._billing.list_invoices_enriched(db, ctx)
        return {**summary, "invoices": invoices[:50]}

    def driver_reports(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        return {"drivers": report_engine.driver_performance(db, ctx.merchant.id)}

    def vehicle_reports(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        return {"vehicles": report_engine.vehicle_usage(db, ctx.merchant.id)}

    def destination_reports(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        return {"destinations": report_engine.top_destinations(db, ctx.merchant.id)}

    def claims_reports(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        return report_engine.claims_summary(db, ctx.merchant.id)

    def overview(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        return {
            "executive": self.executive(db, ctx),
            "delivery_performance": self.delivery_performance(db, ctx),
            "order_volume": self.order_volume(db, ctx),
            "invoice_reports": self.invoice_reports(db, ctx),
            "driver_performance": self.driver_reports(db, ctx),
            "vehicle_usage": self.vehicle_reports(db, ctx),
            "top_destinations": self.destination_reports(db, ctx),
            "claims_summary": self.claims_reports(db, ctx),
            "saved_reports": self.list_saved_reports(ctx),
            "scheduled_reports": self.list_scheduled_reports(ctx),
        }

    def export_csv(self, db: Session, ctx: MerchantContext, report_type: str) -> str:
        rows, fields = self._export_rows(db, ctx, report_type)
        return report_engine.rows_to_csv(rows, fields)

    def export_excel(self, db: Session, ctx: MerchantContext, report_type: str) -> bytes:
        rows, fields = self._export_rows(db, ctx, report_type)
        return report_engine.rows_to_excel(rows, fields, sheet_name=report_type)

    def _export_rows(self, db: Session, ctx: MerchantContext, report_type: str) -> tuple[list[dict], list[str]]:
        if report_type == "drivers":
            rows = report_engine.driver_performance(db, ctx.merchant.id)
            return rows, ["driver_id", "name", "orders", "delivered", "failed", "success_percent"]
        if report_type == "vehicles":
            rows = report_engine.vehicle_usage(db, ctx.merchant.id)
            return rows, ["vehicle_id", "label", "vehicle_class", "orders"]
        if report_type == "destinations":
            rows = report_engine.top_destinations(db, ctx.merchant.id)
            return rows, ["destination", "count"]
        if report_type == "claims":
            data = report_engine.claims_summary(db, ctx.merchant.id)
            rows = [{"type": k, "count": v} for k, v in data.get("by_type", {}).items()]
            return rows, ["type", "count"]
        if report_type == "invoices":
            rows = self._billing.list_invoices_enriched(db, ctx)
            return rows, [
                "invoice_number",
                "order_number",
                "status",
                "amount_cents",
                "tax_cents",
                "outstanding_cents",
                "due_date",
                "created_at",
            ]
        if report_type == "orders":
            rows = report_engine.top_routes(db, ctx.merchant.id, limit=100)
            return rows, ["route", "count"]
        # executive / delivery default
        data = self.delivery_performance(db, ctx)
        rows = [data]
        return rows, list(data.keys())

    def list_saved_reports(self, ctx: MerchantContext) -> list[dict[str, Any]]:
        profile = ctx.merchant.profile if isinstance(ctx.merchant.profile, dict) else {}
        return list(profile.get("saved_reports") or [])

    def save_report(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        name: str,
        report_type: str,
        chart_type: str = "bar",
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        profile = dict(ctx.merchant.profile or {})
        items = list(profile.get("saved_reports") or [])
        report = {
            "id": str(uuid.uuid4()),
            "name": name,
            "report_type": report_type,
            "chart_type": chart_type,
            "filters": filters or {},
            "created_at": datetime.now(UTC).isoformat(),
            "created_by": ctx.user.id,
        }
        items.append(report)
        profile["saved_reports"] = items
        ctx.merchant.profile = profile
        db.commit()
        return report

    def delete_saved_report(self, db: Session, ctx: MerchantContext, report_id: str) -> None:
        profile = dict(ctx.merchant.profile or {})
        items = [r for r in profile.get("saved_reports") or [] if r.get("id") != report_id]
        profile["saved_reports"] = items
        ctx.merchant.profile = profile
        db.commit()

    def list_scheduled_reports(self, ctx: MerchantContext) -> list[dict[str, Any]]:
        profile = ctx.merchant.profile if isinstance(ctx.merchant.profile, dict) else {}
        return list(profile.get("scheduled_reports") or [])

    def save_scheduled_report(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        name: str,
        report_type: str,
        schedule: str,
        email: str,
    ) -> dict[str, Any]:
        profile = dict(ctx.merchant.profile or {})
        items = list(profile.get("scheduled_reports") or [])
        job = {
            "id": str(uuid.uuid4()),
            "name": name,
            "report_type": report_type,
            "schedule": schedule,
            "email": email,
            "active": True,
            "created_at": datetime.now(UTC).isoformat(),
        }
        items.append(job)
        profile["scheduled_reports"] = items
        ctx.merchant.profile = profile
        db.commit()
        return job
