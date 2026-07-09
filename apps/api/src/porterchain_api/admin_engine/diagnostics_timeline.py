"""Control Tower timeline for domain events."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.models import DomainEvent


class ControlTowerTimeline:
    def __init__(self, db: Session) -> None:
        self._db = db

    def recent(self, *, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._db.query(DomainEvent).order_by(DomainEvent.occurred_at.desc()).limit(limit).all()
        return [
            {
                "event_type": e.event_type,
                "aggregate_type": e.aggregate_type,
                "at": e.occurred_at.isoformat() if e.occurred_at else None,
                "correlation_id": e.correlation_id,
            }
            for e in rows
        ]
