"""Driver timesheets (from driver_shifts) and weekly availability schedule.

Availability is stored on ``driver.performance["availability_schedule"]`` (same JSON pattern
as app_settings): ``{"mon": [{"start": "08:00", "end": "16:00"}], ...}`` in the driver's local time.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
TZ = ZoneInfo("America/Toronto")
MAX_WEEKS = 26


class ScheduleError(ValueError):
    def __init__(self, field: str, code: str):
        super().__init__(f"{field}:{code}")
        self.field = field
        self.code = code


def _worked_minutes(shift: Any, now: datetime) -> int:
    end = shift.ended_at or now
    total = int((end - shift.started_at).total_seconds() // 60)
    return max(0, total - int(shift.break_minutes or 0))


def build_timesheet(shifts: list[Any], *, now: datetime | None = None) -> dict:
    """Group shifts into ISO weeks (Mon start, Toronto time), newest first, with totals."""
    now = now or datetime.now(timezone.utc)
    weeks: dict[str, dict] = {}
    for s in sorted(shifts, key=lambda x: x.started_at, reverse=True):
        local = s.started_at.astimezone(TZ)
        monday = (local - timedelta(days=local.weekday())).date().isoformat()
        week = weeks.setdefault(
            monday, {"week_start": monday, "worked_minutes": 0, "break_minutes": 0, "km": 0.0, "shifts": []}
        )
        worked = _worked_minutes(s, now)
        week["worked_minutes"] += worked
        week["break_minutes"] += int(s.break_minutes or 0)
        week["km"] = round(week["km"] + float(s.mileage_km or 0), 1)
        week["shifts"].append(
            {
                "id": s.id,
                "date": local.date().isoformat(),
                "started_at": s.started_at.isoformat(),
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "worked_minutes": worked,
                "break_minutes": int(s.break_minutes or 0),
                "km": round(float(s.mileage_km or 0), 1),
                "status": s.status,
            }
        )
    out = list(weeks.values())
    return {
        "weeks": out,
        "total_worked_minutes": sum(w["worked_minutes"] for w in out),
        "timezone": "America/Toronto",
    }


def load_timesheet(db: Any, driver_id: str, *, weeks: int = 4, now: datetime | None = None) -> dict:
    from porterchain_api.driver_models import DriverShift

    weeks = max(1, min(int(weeks), MAX_WEEKS))
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(weeks=weeks)
    rows = (
        db.query(DriverShift)
        .filter(DriverShift.driver_id == driver_id, DriverShift.started_at >= since)
        .order_by(DriverShift.started_at.desc())
        .limit(500)
        .all()
    )
    return build_timesheet(rows, now=now)


def clean_schedule(raw: Any) -> dict:
    if not isinstance(raw, dict):
        raise ScheduleError("schedule", "invalid")
    out: dict[str, list[dict]] = {}
    for day in DAYS:
        blocks = raw.get(day) or []
        if not isinstance(blocks, list) or len(blocks) > 3:
            raise ScheduleError(day, "invalid")
        clean = []
        for b in blocks:
            if not isinstance(b, dict) or not _HHMM.match(str(b.get("start"))) or not _HHMM.match(str(b.get("end"))):
                raise ScheduleError(day, "invalid_time")
            if b["start"] >= b["end"]:
                raise ScheduleError(day, "end_before_start")
            clean.append({"start": b["start"], "end": b["end"]})
        clean.sort(key=lambda b: b["start"])
        for a, b in zip(clean, clean[1:]):
            if b["start"] < a["end"]:
                raise ScheduleError(day, "overlap")
        out[day] = clean
    unknown = set(raw) - set(DAYS)
    if unknown:
        raise ScheduleError(sorted(unknown)[0], "unknown_day")
    return out


def read_schedule(driver: Any) -> dict:
    stored = (driver.performance or {}).get("availability_schedule") or {}
    return {day: list(stored.get(day) or []) for day in DAYS}


def save_schedule(db: Any, driver: Any, raw: Any) -> dict:
    clean = clean_schedule(raw)
    perf = dict(driver.performance or {})
    perf["availability_schedule"] = clean
    driver.performance = perf
    db.flush()
    return clean


def weekly_hours(schedule: dict) -> float:
    mins = 0
    for blocks in schedule.values():
        for b in blocks:
            h1, m1 = map(int, b["start"].split(":"))
            h2, m2 = map(int, b["end"].split(":"))
            mins += (h2 * 60 + m2) - (h1 * 60 + m1)
    return round(mins / 60, 1)
