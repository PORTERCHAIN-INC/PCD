"""Workflow and event-bus mixin."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.diagnostics_helpers import (
    EVENT_CONSUMERS,
    EVENT_PUBLISHERS,
    HealthClass,
    _now_iso,
)
from porterchain_api.auth.clerk_registry import is_clerk_configured
from porterchain_api.config import Settings
from porterchain_api.models import DomainEvent
from porterchain_shared.config.settings import get_platform_settings


class DiagnosticsWorkflowsMixin:
    def workflow_scenarios(self, db: Session, settings: Settings) -> dict[str, Any]:
        scenarios = [
            {
                "id": "retail_customer",
                "name": "Website Customer → Quote → Booking → Payment → Dispatch → POD",
                "steps": [
                    "Quote",
                    "Booking Draft",
                    "Clerk Authentication",
                    "Stripe Sandbox Payment",
                    "Order Creation",
                    "Operations Queue",
                    "Route Optimization",
                    "Fleetbase Dispatch",
                    "Driver Assignment",
                    "Pickup",
                    "Delivery",
                    "Proof Of Delivery",
                    "Receipt",
                    "Invoice",
                ],
            },
            {
                "id": "merchant_b2b",
                "name": "Merchant CSV → Contract Pricing → Operations → Billing",
                "steps": [
                    "CSV Upload",
                    "Contract Pricing",
                    "Order Creation",
                    "Operations",
                    "Optimization",
                    "Dispatch",
                    "Delivery",
                    "Billing",
                    "Statement",
                ],
            },
            {
                "id": "admin_ops",
                "name": "Admin Manual Order → Claim → Support → Finance",
                "steps": ["Manual Order", "Dispatch", "Driver", "Claim", "Support", "Finance"],
            },
        ]

        enriched: list[dict[str, Any]] = []
        for sc in scenarios:
            readiness_steps = self._workflow_readiness(db, settings, sc["id"])
            statuses = [s["status"] for s in readiness_steps]
            overall = "healthy"
            if "critical" in statuses:
                overall = "critical"
            elif "warning" in statuses:
                overall = "warning"
            enriched.append({**sc, "overall": overall, "step_checks": readiness_steps})

        return {"scenarios": enriched, "checked_at": _now_iso()}

    def simulate_workflow(self, scenario_id: str, db: Session, settings: Settings) -> dict[str, Any]:
        """Dry-run validation — does not create orders or charge payments."""
        steps = self._workflow_readiness(db, settings, scenario_id)
        logs = [f"{s['step']}: {s['status']} — {s.get('note', '')}" for s in steps]
        overall = "healthy"
        if any(s["status"] == "critical" for s in steps):
            overall = "critical"
        elif any(s["status"] == "warning" for s in steps):
            overall = "warning"
        return {
            "scenario_id": scenario_id,
            "mode": "dry_run",
            "overall": overall,
            "steps": steps,
            "logs": logs,
            "simulated_at": _now_iso(),
        }

    def event_bus_inspector(
        self,
        db: Session,
        *,
        aggregate_filter: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        q = db.query(DomainEvent).order_by(DomainEvent.occurred_at.desc())
        if aggregate_filter:
            filt = aggregate_filter.lower()
            q = q.filter(
                (DomainEvent.aggregate_type.ilike(f"%{filt}%"))
                | (DomainEvent.event_type.ilike(f"%{filt}%"))
            )
        rows = q.limit(limit).all()

        events = []
        for e in rows:
            et = e.event_type
            events.append(
                {
                    "event_name": et,
                    "publisher": EVENT_PUBLISHERS.get(et, e.actor_type or "system"),
                    "consumers": EVENT_CONSUMERS.get(et, ["worker"]),
                    "timestamp": e.occurred_at.isoformat() if e.occurred_at else None,
                    "processing_time_ms": None,
                    "status": "processed",
                    "retry_count": 0,
                    "aggregate_type": e.aggregate_type,
                    "aggregate_id": e.aggregate_id,
                    "correlation_id": e.correlation_id,
                }
            )

        dlq_items = self._read_dlq(get_platform_settings())
        return {
            "events": events,
            "dead_letter_queue": dlq_items,
            "stream_key": "porterchain:events",
            "dlq_stream_key": "porterchain:events:dlq",
            "checked_at": _now_iso(),
        }
    def fleetbase_sync_monitor(self, db: Session) -> dict[str, Any]:
        from porterchain_api.config import get_settings
        from porterchain_api.fleetbase_engine import ErrorQueue
        from porterchain_api.fleetbase_engine.sync_health import assess_fleetbase_sync
        from porterchain_api.fleetbase_models import FleetbaseSyncAudit, FleetbaseSyncJob

        settings = get_settings()
        slo = assess_fleetbase_sync(db, settings)
        stats = ErrorQueue.stats(db)
        pending = stats.get("pending", 0) + stats.get("retrying", 0)
        successful = stats.get("done", 0)
        failed = stats.get("dead", 0)

        by_kind: dict[str, int] = {}
        for kind in ("order", "driver", "vehicle", "route", "webhook"):
            by_kind[kind] = (
                db.query(func.count(FleetbaseSyncJob.id))
                .filter(FleetbaseSyncJob.kind.ilike(f"%{kind}%"))
                .scalar()
                or 0
            )

        recent = (
            db.query(FleetbaseSyncAudit)
            .order_by(FleetbaseSyncAudit.created_at.desc())
            .limit(30)
            .all()
        )

        return {
            "slo": slo,
            "pending_sync": pending,
            "successful_sync": successful,
            "failed_sync": failed,
            "retry_queue": stats.get("retrying", 0),
            "driver_sync": by_kind.get("driver", 0),
            "vehicle_sync": by_kind.get("vehicle", 0),
            "route_sync": by_kind.get("route", 0),
            "order_sync": by_kind.get("order", 0),
            "webhook_status": {
                "recent": [
                    {
                        "direction": a.direction,
                        "kind": a.kind,
                        "status": a.status,
                        "order_id": a.order_id,
                        "message": a.message,
                        "at": a.created_at.isoformat() if a.created_at else None,
                    }
                    for a in recent
                ]
            },
            "dead_letters": [
                {
                    "id": j.id,
                    "kind": j.kind,
                    "direction": j.direction,
                    "order_id": j.order_id,
                    "attempts": j.attempts,
                    "last_error": j.last_error,
                }
                for j in ErrorQueue.list_dead(db, limit=20)
            ],
            "alerts": slo.get("alerts", []),
            "queue_stats": stats,
            "checked_at": _now_iso(),
        }

    def merchant_webhook_delivery_monitor(self, db: Session) -> dict[str, Any]:
        from porterchain_api.merchant_engine.webhook_delivery_health import assess_merchant_webhook_delivery
        from porterchain_api.merchant_models import MerchantWebhookDelivery

        slo = assess_merchant_webhook_delivery(db)
        recent = (
            db.query(MerchantWebhookDelivery)
            .order_by(MerchantWebhookDelivery.created_at.desc())
            .limit(30)
            .all()
        )
        return {
            "slo": slo,
            "recent_deliveries": [
                {
                    "id": row.id,
                    "merchant_id": row.merchant_id,
                    "webhook_id": row.webhook_id,
                    "event_type": row.event_type,
                    "success": row.success,
                    "attempt": row.attempt,
                    "response_status": row.response_status,
                    "error_message": row.error_message,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in recent
            ],
            "alerts": slo.get("alerts", []),
            "checked_at": _now_iso(),
        }

    def execution_metrics_dashboard(self, db: Session) -> dict[str, Any]:
        from porterchain_api.admin_engine.execution_metrics import build_execution_metrics_dashboard
        from porterchain_api.config import get_settings

        settings = get_settings()
        metrics = build_execution_metrics_dashboard(db, settings)
        return {
            **metrics,
            "checked_at": _now_iso(),
        }

    def _workflow_readiness(self, db: Session, settings: Settings, scenario_id: str) -> list[dict[str, Any]]:
        checks: list[dict[str, Any]] = []

        def step(name: str, ok: bool, note: str = "", warn: bool = False) -> None:
            status: HealthClass = "healthy" if ok else ("warning" if warn else "critical")
            checks.append({"step": name, "status": status, "note": note})

        if scenario_id == "retail_customer":
            step("Quote", True, "QuoteService via booking_engine")
            step("Booking Draft", True, "Server-persisted drafts")
            step("Clerk Authentication", is_clerk_configured(settings) or settings.clerk_dev_bypass, "Clerk or dev bypass")
            step("Stripe Sandbox Payment", settings.stripe_secret or settings.stripe_mock, "Stripe or mock", warn=settings.stripe_mock)
            step("Order Creation", True, "PaymentService webhook flow")
            step("Operations Queue", True, "Control Tower")
            step("Route Optimization", True, "Route Center + Valhalla/OSRM")
            step("Fleetbase Dispatch", settings.fleetbase_dispatch_bridge, "Via adapter only")
            step("Driver Assignment", settings.fleetbase_dispatch_bridge, "Fleetbase execution")
            step("Pickup", settings.fleetbase_dispatch_bridge, "Status sync via webhooks")
            step("Delivery", settings.fleetbase_dispatch_bridge, "Tracking translator")
            step("Proof Of Delivery", settings.fleetbase_dispatch_bridge, "POD via adapter")
            step("Receipt", True, "BookingConfirmationService")
            step("Invoice", True, "Finance engine")
        elif scenario_id == "merchant_b2b":
            step("CSV Upload", True, "Merchant portal bulk")
            step("Contract Pricing", True, "Merchant contract overrides")
            step("Order Creation", True, "merchant_engine")
            step("Operations", True, "Shared ops queue")
            step("Optimization", True, "Route Center")
            step("Dispatch", settings.fleetbase_dispatch_bridge, "Adapter")
            step("Delivery", settings.fleetbase_dispatch_bridge, "Fleetbase")
            step("Billing", True, "MerchantBillingService")
            step("Statement", True, "NET billing")
        else:
            step("Manual Order", True, "Admin orders")
            step("Dispatch", settings.fleetbase_dispatch_bridge, "Adapter")
            step("Driver", settings.fleetbase_dispatch_bridge, "Driver engine")
            step("Claim", True, "Claims service")
            step("Support", True, "Support service")
            step("Finance", True, "Finance service")

        return checks
