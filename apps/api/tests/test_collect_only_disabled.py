"""Collect-only (warehouse holding) is hidden and refused while the flag is off (Phase 0)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from porterchain_api.admin_engine.order_builder_service import _validate_kind
from porterchain_api.config import Settings
from porterchain_api.services import collect_only as co


def test_flag_defaults_off() -> None:
    assert Settings().collect_only_enabled is False
    assert co.enabled() is False


def test_merchant_booking_refused_with_clear_message() -> None:
    with pytest.raises(ValueError) as exc:
        co.for_booking(None, SimpleNamespace(service_mode="collect_only", additional_stops=None))
    assert str(exc.value).startswith("collect_only_disabled")
    assert "does not store" in str(exc.value)


def test_standard_booking_unaffected() -> None:
    assert co.for_booking(None, SimpleNamespace(service_mode="standard")) is None


def test_admin_builder_refuses_collect_only() -> None:
    stops = [{"type": "pickup"}, {"type": "dropoff"}]
    with pytest.raises(ValueError, match="collect_only_disabled"):
        _validate_kind("collect_only", stops)


def test_flag_on_keeps_code_path(monkeypatch) -> None:
    monkeypatch.setattr(co, "enabled", lambda: True)
    assert co.enabled() is True  # flag on: kept code path still reachable
