"""Offline reconnect: optimize_route intent auto-applies (preview=False)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from porterchain_api.driver_engine.offline_executor import DriverOfflineExecutor


def test_offline_optimize_route_defaults_preview_false() -> None:
    platform = MagicMock()
    executor = DriverOfflineExecutor(platform=platform)
    db = MagicMock()
    driver = SimpleNamespace(id="drv-1")

    executor.execute(db, driver, "optimize_route", {})

    platform.jobs.optimize_route.assert_called_once_with(db, driver, preview=False)


def test_offline_optimize_alias_honors_preview_flag() -> None:
    platform = MagicMock()
    executor = DriverOfflineExecutor(platform=platform)
    db = MagicMock()
    driver = SimpleNamespace(id="drv-1")

    executor.execute(db, driver, "optimize", {"preview": True})

    platform.jobs.optimize_route.assert_called_once_with(db, driver, preview=True)
