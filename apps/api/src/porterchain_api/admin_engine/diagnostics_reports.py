"""Observability and report generation mixin."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.diagnostics_helpers import _now_iso
from porterchain_api.admin_engine.diagnostics_timeline import ControlTowerTimeline
from porterchain_api.auth.clerk_registry import is_clerk_configured
from porterchain_api.config import Settings
from porterchain_api.booking_models import DomainEvent
from porterchain_api.platform.health import readiness
from porterchain_shared.queue.publisher import queue_depths

logger = logging.getLogger(__name__)


class DiagnosticsReportsMixin:
    def observability(self, db: Session, settings: Settings) -> dict[str, Any]:
        depths = queue_depths()
        ready = readiness(db, settings)

        slow_queries: list[dict[str, Any]] = []
        try:
            if "postgresql" in settings.database_url:
                rows = db.execute(
                    text(
                        "SELECT query, calls, mean_exec_time FROM pg_stat_statements "
                        "ORDER BY mean_exec_time DESC LIMIT 5"
                    )
                ).fetchall()
                slow_queries = [
                    {"query": str(r[0])[:200], "calls": r[1], "mean_ms": round(float(r[2]), 2)} for r in rows
                ]
        except Exception:  # noqa: BLE001
            db.rollback()
            slow_queries = [{"note": "pg_stat_statements extension not available"}]

        recent_errors = (
            db.query(DomainEvent)
            .filter(DomainEvent.event_type.ilike("%failed%"))
            .order_by(DomainEvent.occurred_at.desc())
            .limit(10)
            .all()
        )

        return {
            "structured_logs": {"enabled": True, "format": "json-ready via stdlib logging"},
            "correlation_ids": {"header": "X-Request-ID", "domain_events": True},
            "request_tracing": {"middleware": "RequestIdMiddleware", "status": "active"},
            "api_metrics": {"endpoint": "/metrics", "format": "prometheus"},
            "queue_metrics": depths,
            "worker_metrics": {"queues": depths, "redis": ready.get("checks", {}).get("redis")},
            "error_dashboard": [
                {
                    "event_type": e.event_type,
                    "aggregate_id": e.aggregate_id,
                    "at": e.occurred_at.isoformat() if e.occurred_at else None,
                }
                for e in recent_errors
            ],
            "slow_query_report": slow_queries,
            "system_timeline": ControlTowerTimeline(db).recent(limit=20),
            "checked_at": _now_iso(),
        }

    def generate_reports(self, db: Session, settings: Settings, *, write_files: bool = False) -> dict[str, Any]:
        """Legacy diagnostics reports + optional full E2E enterprise reports."""
        health = self.health_dashboard(db, settings)
        arch = self.architecture_validation(settings)
        modules = self.module_validation(db, settings)
        integration = self.run_platform_validation(db, settings)
        workflows = self.workflow_scenarios(db, settings)
        events = self.event_bus_inspector(db, limit=50)
        day_plan = self.day_plan_monitor(db)
        observability = self.observability(db, settings)

        reports = {
            "SYSTEM_HEALTH_REPORT.md": self._report_health(health),
            "ARCHITECTURE_VALIDATION.md": self._report_architecture(arch),
            "MODULE_VALIDATION.md": self._report_modules(modules),
            "INTEGRATION_VALIDATION.md": self._report_integration(integration),
            "BUSINESS_WORKFLOW_VALIDATION.md": self._report_workflows(workflows),
            "EVENT_BUS_REPORT.md": self._report_events(events),
            "DAY_PLAN_REPORT.md": self._report_day_plan(day_plan),
            "CHAOS_TEST_REPORT.md": self._report_chaos(settings),
            "PERFORMANCE_REPORT.md": self._report_performance(observability),
            "SECURITY_REPORT.md": self._report_security(settings),
            "PRODUCTION_READINESS_SCORE.md": self._report_readiness(health, arch, modules, integration),
        }

        # Enterprise E2E reports (phases 1–10)
        try:
            from porterchain_api.admin_engine.e2e_validation_service import E2EValidationService

            e2e = E2EValidationService()
            e2e_result = e2e.run_full(db, settings, write_files=False, cleanup=True)
            reports.update(e2e_result.get("reports", {}))
        except Exception as exc:  # noqa: BLE001
            logger.warning("E2E validation reports skipped: %s", exc)

        written: list[str] = []
        if write_files and settings.app_env == "local":
            root = Path(__file__).resolve().parents[5]
            for name, content in reports.items():
                path = root / name
                path.write_text(content, encoding="utf-8")
                written.append(str(path))

        return {
            "reports": reports,
            "written_files": written,
            "generated_at": _now_iso(),
        }
    # --- report builders ---

    def _icon(self, status: str) -> str:
        return {"healthy": "✅", "warning": "⚠", "critical": "❌", "pass": "✅", "fail": "❌"}.get(status, "⚠")

    def _report_health(self, health: dict[str, Any]) -> str:
        lines = ["# System Health Report", "", f"Generated: {health['checked_at']}", ""]
        lines.append(f"Overall: {self._icon(health['overall'])} {health['overall']}")
        lines.append("")
        for c in health["components"]:
            lines.append(f"- {self._icon(c['status'])} **{c['name']}** — {c['status']}")
            if c.get("latency_ms"):
                lines.append(f"  - Latency: {c['latency_ms']}ms")
            for e in c.get("errors", []):
                lines.append(f"  - Error: {e}")
        return "\n".join(lines)

    def _report_architecture(self, arch: dict[str, Any]) -> str:
        lines = ["# Architecture Validation", "", f"Overall: {self._icon(arch['overall'])} {arch['overall']}", ""]
        for node in arch["chain"]:
            lines.append(f"- {self._icon(node['status'])} {node['node']}")
        return "\n".join(lines)

    def _report_modules(self, modules: dict[str, Any]) -> str:
        lines = ["# Module Validation", ""]
        for m in modules["modules"]:
            lines.append(f"- {self._icon(m['status'])} {m['name']}")
        return "\n".join(lines)

    def _report_integration(self, integration: dict[str, Any]) -> str:
        lines = ["# Integration Validation", ""]
        for r in integration["results"]:
            lines.append(f"- {self._icon(r['status'])} {r['name']} ({r['execution_ms']}ms)")
        return "\n".join(lines)

    def _report_workflows(self, workflows: dict[str, Any]) -> str:
        lines = ["# Business Workflow Validation", ""]
        for sc in workflows["scenarios"]:
            lines.append(f"## {sc['name']}")
            lines.append(f"Overall: {self._icon(sc['overall'])} {sc['overall']}")
            for step in sc.get("step_checks", []):
                lines.append(f"- {self._icon(step['status'])} {step['step']}")
            lines.append("")
        return "\n".join(lines)

    def _report_events(self, events: dict[str, Any]) -> str:
        lines = ["# Event Bus Report", "", f"Recent events: {len(events['events'])}", ""]
        for e in events["events"][:20]:
            lines.append(f"- `{e['event_name']}` @ {e['timestamp']}")
        return "\n".join(lines)

    def _report_day_plan(self, plan: dict[str, Any]) -> str:
        return "\n".join(
            [
                "# Day Plan Report",
                "",
                f"- Engine: {plan.get('engine', 'porterchain')}",
                f"- Solver: {plan.get('solver', 'ortools')}",
                f"- Road cost: {plan.get('road_cost', 'valhalla')}",
                f"- Pending runs: {plan.get('pending_runs', 0)}",
                f"- Ready runs: {plan.get('ready_runs', 0)}",
                f"- Failed runs: {plan.get('failed_runs', 0)}",
            ]
        )

    def _report_chaos(self, settings: Settings) -> str:
        return "# Chaos Test Report\n\nRun individual scenarios via POST /v1/admin/diagnostics/chaos/{scenario}\n"

    def _report_performance(self, obs: dict[str, Any]) -> str:
        lines = ["# Performance Report", "", "## Queue Metrics", json.dumps(obs["queue_metrics"], indent=2)]
        return "\n".join(lines)

    def _report_security(self, settings: Settings) -> str:
        lines = [
            "# Security Report",
            "",
            f"- Clerk: {'configured' if is_clerk_configured(settings) else 'dev bypass' if settings.clerk_dev_bypass else 'missing'}",
            f"- Stripe webhook secret: {'yes' if settings.stripe_webhook_secret else 'no'}",
            f"- Dispatch engine: {settings.dispatch_engine or 'porterchain'}",
        ]
        return "\n".join(lines)

    def _report_readiness(
        self,
        health: dict[str, Any],
        arch: dict[str, Any],
        modules: dict[str, Any],
        integration: dict[str, Any],
    ) -> str:
        score = 100
        score -= health["summary"].get("critical", 0) * 10
        score -= health["summary"].get("warning", 0) * 3
        score -= integration["summary"].get("fail", 0) * 5
        score = max(0, min(100, score))
        grade = "Production Ready" if score >= 85 else "Needs Attention" if score >= 70 else "Not Ready"
        return "\n".join(
            [
                "# Production Readiness Score",
                "",
                f"**Score: {score}/100** — {grade}",
                "",
                f"- Health: {self._icon(health['overall'])} {health['overall']}",
                f"- Architecture: {self._icon(arch['overall'])} {arch['overall']}",
                f"- Modules: {modules['summary']}",
                f"- Integration tests: pass={integration['summary']['pass']} fail={integration['summary']['fail']}",
            ]
        )
