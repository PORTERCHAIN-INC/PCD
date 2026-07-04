"""Driver API application service — business orchestration for driver portal (masterrule §3)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.driver_engine.auth_service import DriverAuthService
from porterchain_api.driver_engine.fleetbase_bridge import DriverFleetbaseBridge
from porterchain_api.driver_engine.offline_executor import DriverOfflineExecutor
from porterchain_driver import DriverPlatform

T = TypeVar("T")


class DriverApiService:
    """Central driver portal service — routers delegate here; owns commits and Fleetbase bridge."""

    def __init__(self) -> None:
        self.platform = DriverPlatform()
        self.auth = DriverAuthService()

    @staticmethod
    def fleetbase_bridge(settings: Settings) -> DriverFleetbaseBridge:
        return DriverFleetbaseBridge(settings)

    @staticmethod
    def persist(db: Session, fn: Callable[[], T]) -> T:
        result = fn()
        db.commit()
        return result

    def offline_executor(self, db: Session, settings: Settings) -> DriverOfflineExecutor:
        bridge = self.fleetbase_bridge(settings)
        executor = DriverOfflineExecutor(self.platform)

        class _BridgeExecutor:
            def execute(self, driver: Any, action_type: str, payload: dict) -> None:
                executor.execute(db, driver, action_type, payload, fleetbase_bridge=bridge)

        return _BridgeExecutor()
