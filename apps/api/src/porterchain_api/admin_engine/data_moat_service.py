"""Admin data moat reporting — network benchmarks (§8.2)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.reporting import data_moat


class AdminDataMoatService:
    def network_benchmarks(self, db: Session, *, window_days: int = 30) -> dict[str, Any]:
        return {
            "dwell_time": data_moat.dwell_time_dataset(db, window_days=window_days),
            "network_sla": data_moat.network_sla_benchmark(db, window_days=window_days),
            "margin_intelligence": data_moat.margin_intelligence(db, window_days=window_days),
        }

    def merchant_benchmarks(self, db: Session, merchant_id: str, *, window_days: int = 30) -> dict[str, Any]:
        return {
            "merchant_id": merchant_id,
            "dwell_time": data_moat.dwell_time_dataset(db, merchant_id=merchant_id, window_days=window_days),
            "margin_intelligence": data_moat.margin_intelligence(
                db, merchant_id=merchant_id, window_days=window_days
            ),
        }

    def own_ping_eta(self, db: Session, settings: Settings, order_id: str) -> dict[str, Any] | None:
        return data_moat.own_ping_eta(db, settings, order_id)
