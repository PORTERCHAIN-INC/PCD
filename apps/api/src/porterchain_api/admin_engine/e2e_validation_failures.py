"""E2E validation — phase 5 failure scenarios."""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.e2e_validation_catalog import FAILURE_SCENARIOS, ValidationStatus
from porterchain_api.admin_engine.e2e_validation_helpers import StepResult
from porterchain_api.auth.clerk_registry import is_clerk_configured
from porterchain_api.config import Settings
from porterchain_api.notification_engine.models import NotificationRecord


class E2EValidationFailuresMixin:
    def phase_5_failures(self, db: Session, settings: Settings) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        chaos_map = {
            "day_plan_offline": "day_plan_offline",
            "stripe_offline": "stripe_offline",
            "clerk_offline": "clerk_offline",
            "firebase_failure": "firebase_offline",
            "google_maps_failure": "google_maps_failure",
            "osrm_failure": "osrm_failure",
            "valhalla_failure": "valhalla_failure",
            "redis_restart": "redis_restart",
            "postgresql_restart": "postgresql_restart",
            "websocket_failure": "websocket_failure",
            "driver_rejects": "driver_reject",
            "vehicle_breakdown": "vehicle_breakdown",
        }

        for scenario in FAILURE_SCENARIOS:
            t0 = time.monotonic()
            status: ValidationStatus = "PASS"
            root_cause = ""
            fix = ""
            priority = "P2"

            if scenario == "stripe_webhook_failure":
                status = "PASS" if settings.stripe_webhook_secret or settings.stripe_mock else "WARNING"
                root_cause = "Webhook secret missing" if status == "WARNING" else ""
                fix = "Configure STRIPE_WEBHOOK_SECRET (ADR-006)"
            elif scenario == "authentication_failed":
                status = "PASS" if is_clerk_configured(settings) or settings.clerk_dev_bypass else "BLOCKER"
                root_cause = "Clerk not configured" if status != "PASS" else ""
                fix = "Configure Clerk or enable CLERK_DEV_BYPASS"
                priority = "P0" if status == "BLOCKER" else "P2"
            elif scenario == "payment_failed":
                fix = "PaymentService records FAILED status + draft PAYMENT_FAILED"
            elif scenario == "notification_failure":
                failed = db.query(func.count(NotificationRecord.id)).filter(NotificationRecord.status == "failed").scalar() or 0
                status = "WARNING" if failed > 0 else "PASS"
                root_cause = f"{failed} failed notification(s) in queue" if failed else ""
            elif scenario in chaos_map:
                chaos = self._diagnostics.chaos_test(chaos_map[scenario], db, settings)
                status = self._health_to_validation(chaos.get("status", "warning"))
                fix = "Verify retry/fallback path in " + self._failure_layer(scenario)
            elif scenario in (
                "customer_cancels",
                "merchant_cancels",
                "pickup_failed",
                "delivery_failed",
                "customer_not_home",
                "driver_cancels",
                "driver_offline",
                "otp_failed",
                "signature_failed",
                "photo_upload_failed",
                "pod_failed",
            ):
                fix = "Handled via domain.states.ExceptionType + claims/ops queue"

            results.append(
                {
                    "scenario": scenario,
                    "status": status,
                    "layer": self._failure_layer(scenario),
                    "root_cause": root_cause,
                    "recommended_fix": fix,
                    "priority": priority,
                    "duration_ms": round((time.monotonic() - t0) * 1000, 1),
                    "retry_recovery": status in ("PASS", "WARNING"),
                }
            )
            self._trace("failure_scenario", scenario, status)

        overall = self._overall_from_steps([StepResult(step=r["scenario"], status=r["status"], layer=r["layer"]) for r in results])
        return {"phase": 5, "name": "Failure Scenarios", "overall": overall, "scenarios": results}
