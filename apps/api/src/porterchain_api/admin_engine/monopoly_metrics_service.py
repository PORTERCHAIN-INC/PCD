"""§9.2 monopoly metrics admin service."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.reporting.monopoly_metrics import monopoly_snapshot


class MonopolyMetricsService:
    def snapshot(self, db: Session, *, window_days: int = 30) -> dict[str, Any]:
        return monopoly_snapshot(db, window_days=window_days)
