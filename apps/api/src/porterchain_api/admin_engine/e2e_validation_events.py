"""E2E validation — phase 6 event bus."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.diagnostics_service import EVENT_CONSUMERS
from porterchain_api.admin_engine.e2e_validation_catalog import (
    REQUIRED_EVENTS,
    ValidationStatus,
)
from porterchain_api.admin_engine.e2e_validation_helpers import StepResult
from porterchain_api.booking_models import DomainEvent


class E2EValidationEventsMixin:
    def phase_6_event_bus(self, db: Session) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []
        for spec in REQUIRED_EVENTS:
            count = (
                db.query(func.count(DomainEvent.id))
                .filter(DomainEvent.event_type == spec["event_type"])
                .scalar()
                or 0
            )
            recent = (
                db.query(DomainEvent)
                .filter(DomainEvent.event_type == spec["event_type"])
                .order_by(DomainEvent.occurred_at.desc())
                .first()
            )
            status: ValidationStatus = "PASS" if count > 0 or recent else "WARNING"
            if spec["alias"] in ("ReturnRequested", "ReturnApproved", "RefundCompleted") and count == 0:
                status = "WARNING"
            checks.append(
                {
                    "event": spec["alias"],
                    "event_type": spec["event_type"],
                    "publisher": spec["publisher"],
                    "subscribers": EVENT_CONSUMERS.get(spec["event_type"], ["worker"]),
                    "occurrence_count": count,
                    "last_seen": recent.occurred_at.isoformat() if recent and recent.occurred_at else None,
                    "status": status,
                }
            )

        inspector = self._diagnostics.event_bus_inspector(db, limit=50)
        overall = self._overall_from_steps(
            [StepResult(step=c["event"], status=c["status"], layer="event_bus") for c in checks]
        )
        return {
            "phase": 6,
            "name": "Event Bus Validation",
            "overall": overall,
            "events": checks,
            "dead_letter_queue": inspector.get("dead_letter_queue", []),
            "recent_events": inspector.get("events", [])[:20],
        }
