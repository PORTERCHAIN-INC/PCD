"""Analytics ETL — removed one-SoT cleanup (tables dropped).

Former Phase-2 scaffold wrote analytics_events / analytics_stop_legs with zero
production callers. Stubs remain so imports do not break; they always skip.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import Settings


def analytics_enabled(settings: Settings) -> bool:
    return False


def ingest_domain_event(
    db: Session,
    *,
    event_type: str,
    aggregate_id: str,
    payload: dict[str, Any],
    occurred_at: datetime | None = None,
) -> dict[str, Any]:
    return {"status": "skipped", "reason": "analytics_tables_removed"}


def ingest_stop_leg(
    db: Session,
    *,
    order_id: str,
    leg_index: int,
    lat: float,
    lng: float,
    recorded_at: datetime | None = None,
) -> dict[str, Any]:
    return {"status": "skipped", "reason": "analytics_tables_removed"}
