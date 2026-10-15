"""Go on duty with a shift already open: resume same-day, close stale, never refuse."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

from porterchain_driver.shift import PRETRIP_ITEMS, STALE_SHIFT_AFTER, ShiftService

CHECKS = {key: True for key, _ in PRETRIP_ITEMS}


def _svc(active):
    svc = ShiftService.__new__(ShiftService)
    svc._require_approved = MagicMock()
    svc._active_shift = MagicMock(side_effect=[active, None])
    svc._log = MagicMock()
    svc._emit = MagicMock()
    svc.snapshot = MagicMock(return_value={"shift_active": True})
    svc.end_shift = MagicMock()
    return svc


def test_same_day_open_shift_is_resumed_not_refused() -> None:
    shift = SimpleNamespace(id="s1", started_at=datetime.now(UTC) - timedelta(hours=2), meta={}, route_id="r1")
    driver = SimpleNamespace(id="d1", is_online=False, availability="offline")
    svc = _svc(shift)
    out = svc.start_shift(MagicMock(), driver, pretrip=CHECKS)
    assert out == {"shift_active": True}
    assert driver.is_online is True and driver.availability == "idle"
    assert shift.meta["pretrip"]["tires"] is True
    svc.end_shift.assert_not_called()
    assert svc._log.call_args.args[3] == "shift_resumed"


def test_naive_started_at_is_treated_as_utc() -> None:
    shift = SimpleNamespace(id="s1", started_at=datetime.now(UTC).replace(tzinfo=None), meta=None, route_id=None)
    driver = SimpleNamespace(id="d1", is_online=False, availability=None)
    svc = _svc(shift)
    svc.start_shift(MagicMock(), driver, pretrip=CHECKS)
    assert driver.is_online is True
    svc.end_shift.assert_not_called()


def test_stale_open_shift_is_closed_then_new_one_started() -> None:
    shift = SimpleNamespace(id="s0", started_at=datetime.now(UTC) - STALE_SHIFT_AFTER - timedelta(minutes=1), meta={}, route_id=None)
    driver = SimpleNamespace(id="d1", is_online=False, availability="offline")
    svc = _svc(shift)
    db = MagicMock()
    # Stop after closing: the fresh-shift path needs a real DB; prove end_shift ran first.
    svc.end_shift.side_effect = RuntimeError("closed")
    try:
        svc.start_shift(db, driver, pretrip=CHECKS)
    except RuntimeError as exc:
        assert str(exc) == "closed"
    svc.end_shift.assert_called_once_with(db, driver)
