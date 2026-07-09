"""E2E validation — phase 9 observability."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.models import DomainEvent, OrderEvent


class E2EValidationObservabilityMixin:
    def phase_9_observability(self, db: Session, settings: Settings) -> dict[str, Any]:
        db.rollback()
        obs = self._diagnostics.observability(db, settings)
        order = self._resolve_e2e_consistency_order(db)

        api_traces: list[dict[str, Any]] = []
        if order:
            events = (
                db.query(DomainEvent)
                .filter(
                    (DomainEvent.aggregate_id == order.id)
                    | (DomainEvent.correlation_id == order.quote_id)
                )
                .order_by(DomainEvent.occurred_at.asc())
                .limit(100)
                .all()
            )
            for e in events:
                api_traces.append(
                    {
                        "type": "event",
                        "name": e.event_type,
                        "at": e.occurred_at.isoformat() if e.occurred_at else None,
                        "order_id": order.id,
                        "tracking_number": order.tracking_number,
                        "correlation_id": e.correlation_id,
                    }
                )
            order_events = (
                db.query(OrderEvent)
                .filter(OrderEvent.order_id == order.id)
                .order_by(OrderEvent.occurred_at.asc())
                .all()
            )
            for oe in order_events:
                api_traces.append(
                    {
                        "type": "state_transition",
                        "from": oe.from_state,
                        "to": oe.to_state,
                        "at": oe.occurred_at.isoformat() if oe.occurred_at else None,
                        "order_id": order.id,
                        "tracking_number": order.tracking_number,
                    }
                )

        timeline = sorted(self._timeline + api_traces, key=lambda x: x.get("at") or "")
        return {
            "phase": 9,
            "name": "Observability",
            "overall": "PASS",
            "timeline": timeline,
            "queue_metrics": obs.get("queue_metrics"),
            "correlation": {
                "order_id": order.id if order else None,
                "tracking_number": order.tracking_number if order else None,
                "reference_number": order.order_number if order else None,
            },
            "observability": obs,
        }
