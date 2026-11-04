"""L185: the 16h auto clock-out is recorded at the 16h mark (break time added), not 'now'."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from porterchain_driver.shift import ShiftService


class _Db:
    def flush(self):
        pass


def _svc(shift):
    svc = ShiftService()
    svc._active_shift = lambda db, driver_id: shift if shift.status != "ended" else None
    svc._working_minutes = lambda s: int((datetime.now(UTC) - s.started_at).total_seconds() // 60) - s.break_minutes

    def end_shift(db, driver):
        shift.status, shift.ended_at = "ended", datetime.now(UTC)
        driver.is_online, driver.availability = False, "offline"

    svc.end_shift = end_shift
    svc._log = lambda *a, **k: None
    return svc


def test_auto_clockout_capped_at_limit():
    start = datetime.now(UTC) - timedelta(days=4)
    shift = SimpleNamespace(id="s1", status="active", started_at=start, ended_at=None, break_minutes=30)
    driver = SimpleNamespace(id="d1", is_online=True, availability="online")
    assert _svc(shift).enforce_shift_limit(_Db(), driver) is True
    assert shift.ended_at == start + timedelta(hours=16, minutes=30)
    assert driver.is_online is False


def test_short_shift_untouched():
    shift = SimpleNamespace(id="s1", status="active", started_at=datetime.now(UTC) - timedelta(hours=2), ended_at=None, break_minutes=0)
    driver = SimpleNamespace(id="d1", is_online=True, availability="online")
    assert _svc(shift).enforce_shift_limit(_Db(), driver) is False
    assert shift.ended_at is None and driver.is_online is True
