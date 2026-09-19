"""Ontario clocks. Date filters use America/Toronto, not UTC midnight."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

TORONTO = ZoneInfo("America/Toronto")


def format_datetime_toronto(value: datetime | None) -> str:
    """Wall clock in America/Toronto for merchant print sheets."""
    if value is None:
        return "—"
    dt = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    local = dt.astimezone(TORONTO)
    return local.strftime("%Y-%m-%d %H:%M")


def parse_toronto_day_bound(value: str | None, *, end: bool = False) -> datetime | None:
    """Calendar date the merchant picked → naive UTC instant for DB compare.

    `2026-09-10` and the old `2026-09-10T00:00:00Z` both mean that Toronto day.
    """
    if not value or not str(value).strip():
        return None
    raw = str(value).strip()
    try:
        day = date.fromisoformat(raw[:10])
    except ValueError:
        return None
    clock = time(23, 59, 59) if end else time.min
    local = datetime.combine(day, clock, tzinfo=TORONTO)
    return local.astimezone(UTC).replace(tzinfo=None)
