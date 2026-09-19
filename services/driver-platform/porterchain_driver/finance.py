"""Driver finance facade — delegates to Finance Engine (billing_engine)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class DriverFinanceService:
    def _engine(self):
        from porterchain_api.billing_engine.driver_finance_service import (
            DriverFinanceService as FinanceEngine,
        )

        return FinanceEngine()

    def snapshot(self, db: Session, driver: Any) -> dict[str, Any]:
        return self._engine().driver_earnings_snapshot(db, driver)

    def list_statements(self, db: Session, driver_id: str) -> list[dict[str, Any]]:
        return self._engine().list_statements(db, driver_id)

    def statement_detail(self, db: Session, driver_id: str, statement_id: str) -> dict[str, Any]:
        return self._engine().statement_detail(db, driver_id, statement_id)

    def statement_csv(self, db: Session, driver_id: str, statement_id: str) -> tuple[bytes, str]:
        return self._engine().statement_csv(db, driver_id, statement_id)
