"""Driver earnings — delegates to Finance Engine; credits delivery wallet entries."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

DEFAULT_PER_STOP_CENTS = 850


class EarningsService:
    def _finance(self):
        from porterchain_api.billing_engine.driver_finance_service import DriverFinanceService

        return DriverFinanceService()

    def today_cents(self, db: Session, driver_id: str) -> int:
        return self._finance().period_earnings_cents(db, driver_id, "today")

    def week_cents(self, db: Session, driver_id: str) -> int:
        return self._finance().period_earnings_cents(db, driver_id, "week")

    def month_cents(self, db: Session, driver_id: str) -> int:
        return self._finance().period_earnings_cents(db, driver_id, "month")

    def route_earnings_cents(self, db: Session, driver_id: str, route_id: str) -> int:
        return self._finance().route_earnings_cents(db, driver_id, route_id)

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

        amount = amount_cents if amount_cents is not None else DEFAULT_PER_STOP_CENTS
        return WalletService().credit(
            db, driver, amount_cents=amount, tx_type="delivery", reference_id=order_id, description=description
        )
