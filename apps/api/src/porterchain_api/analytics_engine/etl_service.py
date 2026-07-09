"""Event warehouse ETL — Phase 2 scaffold (§4.1.3).

Runs only when PORTERCHAIN_PHASE2_ANALYTICS=true. Copies domain events and stop
legs into analytics_* tables for batch models.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import Settings


def analytics_enabled(settings: Settings) -> bool:
    return bool(settings.phase2_flags.get("analytics"))


def ingest_domain_event(
    db: Session,
    *,
    event_type: str,
    aggregate_id: str,
    payload: dict[str, Any],
    occurred_at: datetime | None = None,
) -> dict[str, Any]:
    """Insert one row into analytics_events when Phase 2 analytics is enabled."""
    if not analytics_enabled(Settings()):
        return {"status": "skipped", "reason": "phase2_analytics_disabled"}

    from porterchain_api.models import AnalyticsEvent

    row = AnalyticsEvent(
        event_type=event_type,
        aggregate_id=aggregate_id,
        payload=payload,
        occurred_at=occurred_at or datetime.now(UTC),
    )
    db.add(row)
    db.flush()
    return {"status": "ingested", "id": row.id}


def ingest_stop_leg(
    db: Session,
    *,
    order_id: str,
    leg_index: int,
    lat: float,
    lng: float,
    recorded_at: datetime | None = None,
) -> dict[str, Any]:
    """Insert GPS stop leg for analytics feature store (§4.1.1 path)."""
    if not analytics_enabled(Settings()):
        return {"status": "skipped", "reason": "phase2_analytics_disabled"}

    from porterchain_api.models import AnalyticsStopLeg

    row = AnalyticsStopLeg(
        order_id=order_id,
        leg_index=leg_index,
        lat=lat,
        lng=lng,
        recorded_at=recorded_at or datetime.now(UTC),
    )
    db.add(row)
    db.flush()
    return {"status": "ingested", "id": row.id}
