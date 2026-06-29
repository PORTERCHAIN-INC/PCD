"""Driver earnings — today, week, per-route."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class EarningsService:
    DEFAULT_PER_STOP_CENTS = 850

    def today_cents(self, db: Session, driver_id: str) -> int:
        start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        return self._sum_between(db, driver_id, start, datetime.now(UTC))

    def week_cents(self, db: Session, driver_id: str) -> int:
        start = datetime.now(UTC) - timedelta(days=7)
        return self._sum_between(db, driver_id, start, datetime.now(UTC))

    def route_earnings_cents(self, db: Session, driver_id: str, route_id: str) -> int:
        from porterchain_driver.stops import StopsService

        stops = StopsService().stops_for_route(db, driver_id, route_id)
        return len(stops) * self.DEFAULT_PER_STOP_CENTS

    def credit_delivery(
        self,
        db: Session,
        driver: Any,
        *,
        order_id: str,
        amount_cents: int | None = None,
        description: str = "Delivery completed",
    ) -> int:
        from porterchain_driver.wallet import WalletService

        amount = amount_cents if amount_cents is not None else self.DEFAULT_PER_STOP_CENTS
        return WalletService().credit(
            db, driver, amount_cents=amount, tx_type="delivery", reference_id=order_id, description=description
        )

    def _sum_between(self, db: Session, driver_id: str, start: datetime, end: datetime) -> int:
        from porterchain_api.driver_models import DriverWalletTransaction

        rows = (
            db.query(DriverWalletTransaction)
            .filter(
                DriverWalletTransaction.driver_id == driver_id,
                DriverWalletTransaction.amount_cents > 0,
                DriverWalletTransaction.created_at >= start,
                DriverWalletTransaction.created_at <= end,
            )
            .all()
        )
        return sum(r.amount_cents for r in rows)
