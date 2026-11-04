"""Weekly merchant billing (Ravi, 2026-10-31).

A week's business (Mon 00:00 - Sun 24:00, America/Toronto) is invoiced the following
Wednesday and is due the Wednesday after that (end of day, Toronto). After that the
late penalty (settings.late_penalty_pct, 20%) and suspension apply.
All returned datetimes are naive UTC, like the rest of the billing code.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

TORONTO = ZoneInfo("America/Toronto")
WEDNESDAY = 2
TERMS_LABEL = "Weekly: invoiced the Wednesday after the week, due the following Wednesday"
TERMS_LABEL_FR = "Hebdomadaire : facturé le mercredi suivant la semaine, payable le mercredi d'après"


def _local(dt: datetime | None) -> datetime:
    dt = dt or datetime.now(UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(TORONTO)


def _utc_naive(local: datetime) -> datetime:
    return local.astimezone(UTC).replace(tzinfo=None)


def week_bounds(reference: datetime | None = None) -> tuple[datetime, datetime]:
    """The Toronto Mon-Sun week containing ``reference``: [start, end) as naive UTC."""
    day = _local(reference).date()
    monday = day - timedelta(days=day.weekday())
    start = datetime.combine(monday, time.min, tzinfo=TORONTO)
    end = datetime.combine(monday + timedelta(days=7), time.min, tzinfo=TORONTO)
    return _utc_naive(start), _utc_naive(end)


def previous_week_bounds(reference: datetime | None = None) -> tuple[datetime, datetime]:
    start, _ = week_bounds(reference)
    return week_bounds(start.replace(tzinfo=UTC) - timedelta(days=1))


def invoice_day_reached(reference: datetime | None = None) -> bool:
    """Last week is invoiced from Wednesday on (Mon/Tue wait)."""
    return _local(reference).weekday() >= WEDNESDAY


def due_at_for_issue(issued_at: datetime | None) -> datetime:
    """End of day (Toronto) on the first Wednesday after the issue day."""
    day = _local(issued_at).date()
    ahead = (WEDNESDAY - day.weekday()) % 7 or 7
    due_day = day + timedelta(days=ahead)
    return _utc_naive(datetime.combine(due_day, time(23, 59, 59), tzinfo=TORONTO))


def terms_line(period_start: datetime | None, period_end: datetime | None, due_at: datetime | None) -> str:
    """Bilingual lines for the invoice email: week covered and due date."""
    out = []
    if period_start and period_end:
        a = _local(period_start).date()
        # L126: last day covered (handles end-of-day ends like 23:30 as well as midnight).
        b = (_local(period_end) - timedelta(microseconds=1)).date()
        out.append(f"Week / Semaine: {a:%b %d} - {b:%b %d, %Y}")
    if due_at:
        out.append(f"Due / Échéance: {_local(due_at):%a %b %d, %Y} (Toronto)")
    try:
        from porterchain_api.config import get_settings

        pct = f"{float(get_settings().late_penalty_pct):g}"
    except Exception:  # noqa: BLE001 - copy only
        pct = "20"
    out.append(
        f"Terms / Modalités: {TERMS_LABEL} / {TERMS_LABEL_FR}. "
        f"A {pct}% late penalty applies after the due date and new bookings are paused / "
        f"Une pénalité de retard de {pct} % s'applique après l'échéance et les nouvelles réservations sont suspendues."
    )
    return "\n".join(out)
