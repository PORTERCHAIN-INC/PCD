"""L144: 14h long-shift warning, 16h auto clock-out (decision recorded in issues.md)."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from porterchain_driver.shift import ShiftService


def _shift(hours):
    return SimpleNamespace(started_at=datetime.now(UTC) - timedelta(hours=hours), ended_at=None,
                           status="active", break_minutes=0, break_started_at=None, id="s1")


def test_thresholds(db):
    svc = ShiftService()
    assert svc._working_minutes(_shift(15)) >= svc.LONG_SHIFT_WARN_MIN
    assert svc._working_minutes(_shift(15)) < svc.LONG_SHIFT_MAX_MIN


def test_auto_clock_out_at_16h(db, monkeypatch):
    svc = ShiftService()
    sh = _shift(16.5)
    ended = []
    monkeypatch.setattr(svc, "_active_shift", lambda _db, _id: sh)
    monkeypatch.setattr(svc, "end_shift", lambda _db, d: ended.append(d))
    monkeypatch.setattr(svc, "_log", lambda *a, **k: None)
    assert svc.enforce_shift_limit(db, SimpleNamespace(id="d1")) is True
    assert ended


def test_no_clock_out_before_16h(db, monkeypatch):
    svc = ShiftService()
    monkeypatch.setattr(svc, "_active_shift", lambda _db, _id: _shift(10))
    assert svc.enforce_shift_limit(db, SimpleNamespace(id="d1")) is False
