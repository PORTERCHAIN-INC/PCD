"""E2E validation — phase 7 notifications."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.e2e_validation_catalog import (
    NOTIFICATION_AUDIENCES,
    ValidationStatus,
)
from porterchain_api.admin_engine.e2e_validation_helpers import StepResult
from porterchain_api.config import Settings
from porterchain_api.notification_engine.models import NotificationRecord


class E2EValidationNotificationsMixin:
    def phase_7_notifications(self, db: Session, settings: Settings) -> dict[str, Any]:
        audience_results: list[dict[str, Any]] = []
        for audience in NOTIFICATION_AUDIENCES:
            count = (
                db.query(func.count(NotificationRecord.id))
                .filter(NotificationRecord.recipient_type == audience)
                .scalar()
                or 0
            )
            failed = (
                db.query(func.count(NotificationRecord.id))
                .filter(
                    NotificationRecord.recipient_type == audience,
                    NotificationRecord.status == "failed",
                )
                .scalar()
                or 0
            )
            status: ValidationStatus = "PASS"
            if failed > 0:
                status = "WARNING"
            if audience == "driver" and not settings.firebase_project_id if hasattr(settings, "firebase_project_id") else True:
                pass
            audience_results.append(
                {
                    "audience": audience,
                    "total": count,
                    "failed": failed,
                    "delivered": count - failed,
                    "status": status,
                    "retries": "RETRY_DELAYS_SEC in notification_engine",
                }
            )

        firebase = self._diagnostics._probe_firebase(
            __import__("porterchain_shared.config.settings", fromlist=["get_platform_settings"]).get_platform_settings()
        )
        overall = self._overall_from_steps(
            [StepResult(step=a["audience"], status=a["status"], layer="notification_engine") for a in audience_results]
        )
        return {
            "phase": 7,
            "name": "Notification Validation",
            "overall": overall,
            "audiences": audience_results,
            "firebase": firebase,
        }
