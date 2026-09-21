"""Driver dashboard — today's earnings, stops, performance summary."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from porterchain_driver.types import DashboardSnapshot

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class DashboardService:
    def snapshot(self, db: Session, driver: Any) -> DashboardSnapshot:
        from porterchain_driver.earnings import EarningsService
        from porterchain_driver.stops import StopsService
        from porterchain_driver.bonuses import BonusesService
        from porterchain_driver.performance import PerformanceService
        from porterchain_driver.documents import DocumentsService

        from porterchain_api.driver_engine.wallet_ledger import wallet_balance_cents as ledger_balance

        earnings = EarningsService().today_cents(db, driver.id)
        stops = StopsService().today_stops(db, driver.id)
        completed = sum(1 for s in stops if s.status in ("delivered", "completed", "POD_COMPLETED"))
        perf = PerformanceService().score(driver)
        docs = DocumentsService().pending_count(driver)

        return DashboardSnapshot(
            driver_id=driver.id,
            todays_earnings_cents=earnings,
            todays_stops_total=len(stops),
            todays_stops_completed=completed,
            wallet_balance_cents=ledger_balance(
                db, driver.id, cached_cents=driver.wallet_balance_cents or 0
            ),
            is_online=bool(driver.is_online),
            availability=driver.availability or "offline",
            rating=driver.rating,
            active_route_id=_active_route_id(stops),
            bonuses_available=BonusesService().available_count(db, driver.id),
            performance_score=perf,
            pending_documents=docs,
        )


def _active_route_id(stops: list) -> str | None:
    if not stops:
        return None
    today = datetime.now(UTC).date().isoformat()
    return f"route-{today}"
