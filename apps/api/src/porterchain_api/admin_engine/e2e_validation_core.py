"""E2E validation orchestration, auto-fix, and shared result helpers."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.diagnostics_service import AdminDiagnosticsService
from porterchain_api.admin_engine.e2e_validation_catalog import DEFAULT_MERCHANT_BULK_COUNT, E2E_MARKER, ValidationStatus
from porterchain_api.admin_engine.e2e_validation_helpers import StepResult, _now_iso
from porterchain_api.auth.clerk_registry import is_clerk_configured
from porterchain_api.config import Settings
from porterchain_api.booking_models import Order

logger = logging.getLogger(__name__)


class E2EValidationCoreMixin:
    """Orchestration, auto-fix, tracing, and phase result aggregation."""

    def __init__(self) -> None:
        self._diagnostics = AdminDiagnosticsService()
        self._timeline: list[dict[str, Any]] = []

    def run_full(
        self,
        db: Session,
        settings: Settings,
        *,
        write_files: bool = False,
        cleanup: bool = True,
        merchant_order_count: int = DEFAULT_MERCHANT_BULK_COUNT,
    ) -> dict[str, Any]:
        start = time.monotonic()
        self._timeline = []
        auto_fixes = self.auto_fix_configuration(db, settings)

        def _phase(name: str, fn):
            db.rollback()
            try:
                result = fn()
                db.commit()
                return result
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                return {
                    "phase": name,
                    "name": f"Phase {name}",
                    "overall": "BLOCKER",
                    "error": str(exc)[:500],
                }

        phases = {
            "phase_1_system_layer": _phase("1", lambda: self.phase_1_system_layer(db, settings)),
            "phase_2_forward_logistics": _phase("2", lambda: self.phase_2_forward_logistics(db, settings)),
            "phase_3_merchant": _phase("3", lambda: self.phase_3_merchant(db, settings, order_count=merchant_order_count)),
            "phase_4_reverse_logistics": _phase("4", lambda: self.phase_4_reverse_logistics(db, settings)),
            "phase_5_failures": _phase("5", lambda: self.phase_5_failures(db, settings)),
            "phase_6_event_bus": _phase("6", lambda: self.phase_6_event_bus(db)),
            "phase_7_notifications": _phase("7", lambda: self.phase_7_notifications(db, settings)),
            "phase_8_consistency": _phase("8", lambda: self.phase_8_consistency(db, settings)),
            "phase_9_observability": _phase("9", lambda: self.phase_9_observability(db, settings)),
        }

        if cleanup:
            try:
                self._cleanup_e2e_data(db)
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                logger.warning("E2E cleanup partial failure: %s", exc)

        reports = self.generate_reports(phases, settings, auto_fixes)
        written: list[str] = []
        if write_files:
            root = Path(__file__).resolve().parents[5]
            for name, content in reports.items():
                path = root / name
                path.write_text(content, encoding="utf-8")
                written.append(str(path))

        summary = self._summarize(phases)
        elapsed = (time.monotonic() - start) * 1000
        production_ready = summary["blockers"] == 0 and summary["fails"] == 0

        return {
            "overall": "PASS" if production_ready else ("WARNING" if summary["blockers"] == 0 else "BLOCKER"),
            "production_ready": production_ready,
            "summary": summary,
            "auto_fixes": auto_fixes,
            "phases": phases,
            "timeline": self._timeline,
            "reports": reports,
            "written_files": written,
            "execution_ms": round(elapsed, 1),
            "ran_at": _now_iso(),
        }

    def auto_fix_configuration(self, db: Session, settings: Settings) -> list[dict[str, str]]:
        """Apply safe configuration fixes — never redesign architecture."""
        fixes: list[dict[str, str]] = []

        if settings.app_env == "local":
            if not settings.stripe_secret and not settings.stripe_mock:
                fixes.append(
                    {
                        "fix": "stripe_mock_recommended",
                        "action": "Use STRIPE_MOCK=true for local E2E (masterrule §14)",
                        "applied": "documented",
                    }
                )
            if not is_clerk_configured(settings) and not settings.clerk_dev_bypass:
                fixes.append(
                    {
                        "fix": "clerk_dev_bypass_recommended",
                        "action": "Enable CLERK_DEV_BYPASS=true for local validation",
                        "applied": "documented",
                    }
                )

        return fixes

    def _trace(self, kind: str, name: str, status: str, **extra: Any) -> None:
        self._timeline.append({"kind": kind, "name": name, "status": status, "at": _now_iso(), **extra})

    def _health_to_validation(self, health: str) -> ValidationStatus:
        h = health.lower()
        if h in ("healthy", "pass", "ok"):
            return "PASS"
        if h in ("warning", "degraded", "mock"):
            return "WARNING"
        if h == "critical":
            return "BLOCKER"
        return "FAIL"

    def _overall_from_steps(self, steps: list[StepResult]) -> ValidationStatus:
        if any(s.status == "BLOCKER" for s in steps):
            return "BLOCKER"
        if any(s.status == "FAIL" for s in steps):
            return "FAIL"
        if any(s.status == "WARNING" for s in steps):
            return "WARNING"
        return "PASS"

    def _phase_result(self, num: int, name: str, steps: list[StepResult], *, extra: dict | None = None) -> dict[str, Any]:
        overall = self._overall_from_steps(steps)
        out: dict[str, Any] = {
            "phase": num,
            "name": name,
            "overall": overall,
            "steps": [s.as_dict() for s in steps],
            "summary": {
                "pass": sum(1 for s in steps if s.status == "PASS"),
                "warning": sum(1 for s in steps if s.status == "WARNING"),
                "fail": sum(1 for s in steps if s.status == "FAIL"),
                "blocker": sum(1 for s in steps if s.status == "BLOCKER"),
            },
        }
        if extra:
            out.update(extra)
        return out

    def _summarize(self, phases: dict[str, Any]) -> dict[str, int]:
        totals = {"pass": 0, "warning": 0, "fails": 0, "blockers": 0, "total": 0}
        for phase in phases.values():
            if "steps" in phase:
                for s in phase["steps"]:
                    totals["total"] += 1
                    st = s.get("status", "FAIL")
                    if st == "PASS":
                        totals["pass"] += 1
                    elif st == "WARNING":
                        totals["warning"] += 1
                    elif st == "BLOCKER":
                        totals["blockers"] += 1
                    else:
                        totals["fails"] += 1
            if "scenarios" in phase:
                for s in phase["scenarios"]:
                    totals["total"] += 1
                    st = s.get("status", "FAIL")
                    if st == "PASS":
                        totals["pass"] += 1
                    elif st == "WARNING":
                        totals["warning"] += 1
                    elif st == "BLOCKER":
                        totals["blockers"] += 1
                    else:
                        totals["fails"] += 1
            if "events" in phase:
                for e in phase["events"]:
                    totals["total"] += 1
                    st = e.get("status", "FAIL")
                    if st == "PASS":
                        totals["pass"] += 1
                    elif st == "WARNING":
                        totals["warning"] += 1
                    else:
                        totals["fails"] += 1
        return totals

    def _cleanup_e2e_data(self, db: Session) -> int:
        order_ids = [row[0] for row in db.query(Order.id).filter(Order.internal_reference == E2E_MARKER).all()]
        if not order_ids:
            return 0
        for table in (
            "billing_ledger_entries",
            "claims",
            "order_events",
            "payments",
            "invoices",
            "bookings",
            "support_tickets",
        ):
            try:
                db.execute(text(f"DELETE FROM {table} WHERE order_id = ANY(:ids)"), {"ids": order_ids})
            except Exception:  # noqa: BLE001
                db.rollback()
        try:
            db.execute(
                text("DELETE FROM notification_records WHERE context::text LIKE :marker"),
                {"marker": f"%{E2E_MARKER}%"},
            )
        except Exception:  # noqa: BLE001
            db.rollback()
        db.execute(
            text("DELETE FROM domain_events WHERE aggregate_id = ANY(:ids)"),
            {"ids": order_ids},
        )
        db.query(Order).filter(Order.internal_reference == E2E_MARKER).delete(synchronize_session=False)
        db.commit()
        return len(order_ids)

    def _failure_layer(self, scenario: str) -> str:
        mapping = {
            "stripe_webhook_failure": "billing_engine",
            "day_plan_offline": "dispatch_engine",
            "google_maps_failure": "integrations",
            "authentication_failed": "auth",
            "notification_failure": "notification_engine",
        }
        return mapping.get(scenario, "operations")
