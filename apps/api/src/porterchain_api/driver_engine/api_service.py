"""Driver API application service — business orchestration for driver portal (masterrule §3)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.driver_engine.auth_service import DriverAuthService
from porterchain_api.driver_engine.offline_executor import DriverOfflineExecutor
from porterchain_driver import DriverPlatform

T = TypeVar("T")


class DriverApiService:
    """Central driver portal service — routers delegate here; owns commits."""

    def __init__(self) -> None:
        self.platform = DriverPlatform()
        self.auth = DriverAuthService()


    @staticmethod
    def persist(db: Session, fn: Callable[[], T]) -> T:
        result = fn()
        db.commit()
        return result

    @staticmethod
    def require_assigned_order(db: Session, *, driver_id: str, order_id: str) -> Any:
        """Load the order and reject drivers who are not assigned to it."""
        from porterchain_api.booking_models import Order

        order = db.get(Order, order_id)
        if not order:
            raise LookupError("order_not_found")
        if order.assigned_driver_id and order.assigned_driver_id != driver_id:
            raise PermissionError("not_assigned_driver")
        return order

    def offline_executor(self, db: Session, settings: Settings) -> DriverOfflineExecutor:
        del settings
        executor = DriverOfflineExecutor(self.platform)

        class _Executor:
            def execute(self, driver: Any, action_type: str, payload: dict) -> None:
                executor.execute(db, driver, action_type, payload)

        return _Executor()
