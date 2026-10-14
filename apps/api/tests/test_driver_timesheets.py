from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from porterchain_api.routers.driver import timesheets as route
from porterchain_driver import timesheets as ts

UTC = timezone.utc


def _shift(sid, start, hours, brk=30, km=40.0, ended=True):
    s = datetime(2026, 10, *start, tzinfo=UTC) if isinstance(start, tuple) else start
    return SimpleNamespace(id=sid, started_at=s, ended_at=s + timedelta(hours=hours) if ended else None,
                           break_minutes=brk, mileage_km=km, status="ended" if ended else "active")


def test_timesheet_groups_by_toronto_week_with_totals():
    shifts = [
        _shift("a", (12, 13), 8),          # Mon Oct 12
        _shift("b", (14, 13), 6, brk=0),   # Wed Oct 14
        _shift("c", (9, 13), 4, km=10.5),  # Fri Oct 9 (previous week)
    ]
    out = ts.build_timesheet(shifts, now=datetime(2026, 10, 15, tzinfo=UTC))
    assert [w["week_start"] for w in out["weeks"]] == ["2026-10-12", "2026-10-05"]
    assert out["weeks"][0]["worked_minutes"] == 450 + 360
    assert out["weeks"][1]["km"] == 10.5
    assert out["total_worked_minutes"] == 450 + 360 + 210


def test_late_night_utc_shift_lands_on_toronto_day():
    s = _shift("n", datetime(2026, 10, 13, 2, 0, tzinfo=UTC), 2)  # 22:00 Mon Toronto
    out = ts.build_timesheet([s], now=datetime(2026, 10, 15, tzinfo=UTC))
    assert out["weeks"][0]["shifts"][0]["date"] == "2026-10-12"


def test_active_shift_counts_until_now():
    start = datetime(2026, 10, 14, 12, tzinfo=UTC)
    out = ts.build_timesheet([_shift("x", start, 0, brk=0, ended=False)], now=start + timedelta(hours=2))
    assert out["weeks"][0]["shifts"][0]["worked_minutes"] == 120


def _ctx(**perf):
    return SimpleNamespace(driver=SimpleNamespace(id="d1", performance={"rating_avg": 5, **perf}))


def test_schedule_round_trip_and_hours():
    ctx = _ctx()
    with patch.object(route, "db_transaction", lambda db: nullcontext()):
        out = route.put_schedule({"schedule": {"mon": [{"start": "13:00", "end": "17:00"}, {"start": "08:00", "end": "12:00"}],
                                               "sat": [{"start": "09:00", "end": "15:30"}]}}, ctx, db=MagicMock())
    assert out["schedule"]["mon"][0]["start"] == "08:00"
    assert out["weekly_hours"] == 14.5
    assert ctx.driver.performance["rating_avg"] == 5
    assert route.get_schedule(ctx)["schedule"]["sat"] == [{"start": "09:00", "end": "15:30"}]


@pytest.mark.parametrize("sched,field,code", [
    ({"mon": [{"start": "9:00", "end": "10:00"}]}, "mon", "invalid_time"),
    ({"tue": [{"start": "12:00", "end": "11:00"}]}, "tue", "end_before_start"),
    ({"wed": [{"start": "08:00", "end": "12:00"}, {"start": "11:00", "end": "13:00"}]}, "wed", "overlap"),
    ({"funday": []}, "funday", "unknown_day"),
])
def test_schedule_validation(sched, field, code):
    with patch.object(route, "db_transaction", lambda db: nullcontext()), pytest.raises(HTTPException) as e:
        route.put_schedule({"schedule": sched}, _ctx(), db=MagicMock())
    assert e.value.status_code == 422 and e.value.detail == {"field": field, "code": code}
