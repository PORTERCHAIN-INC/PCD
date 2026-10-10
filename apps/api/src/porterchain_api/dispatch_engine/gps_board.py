"""Live GPS board — every on-duty PorterChain driver from Redis last_known.

Duty comes from an open DriverShift; the pin comes from
``last_known``. Drivers without a recent pin are omitted (nothing to plot).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import Driver
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.driver_models import DriverShift
from porterchain_api.platform.last_known import read_last_known

SOURCE_LAST_KNOWN = "last_known"
SOURCE_MISS = "miss"

# Match utilization: shifts started in the last half day.
_SHIFT_LOOKBACK = timedelta(hours=12)


def _active_shifts(db: Session, *, since: datetime) -> dict[str, DriverShift]:
    rows = (
        db.query(DriverShift)
        .filter(DriverShift.started_at >= since)
        .order_by(DriverShift.started_at.desc())
        .all()
    )
    out: dict[str, DriverShift] = {}
    for shift in rows:
        if shift.driver_id in out:
            continue
        if shift.ended_at is not None:
            continue
        if str(shift.status or "").lower() in {"ended", "closed", "complete", "completed"}:
            continue
        out[shift.driver_id] = shift
    return out


def _on_break(shift: DriverShift) -> bool:
    return bool(
        shift.break_started_at is not None
        or str(shift.status or "").lower() in {"on_break", "break"}
    )


def _online(driver: Driver, *, on_break: bool) -> bool:
    if on_break:
        return True
    return bool(driver.is_online) or driver.availability == "online"


def board_pins(db: Session) -> tuple[list[dict[str, Any]], str]:
    """Return map pins for approved drivers with an open shift and a Redis pin."""
    since = datetime.now(UTC) - _SHIFT_LOOKBACK
    shifts = _active_shifts(db, since=since)
    if not shifts:
        return [], SOURCE_MISS

    drivers = (
        db.query(Driver)
        .filter(
            Driver.id.in_(list(shifts.keys())),
            Driver.status == DriverStatus.APPROVED.value,
        )
        .all()
    )
    pins: list[dict[str, Any]] = []
    for driver in drivers:
        shift = shifts.get(driver.id)
        if shift is None:
            continue
        known = read_last_known(driver.id)
        if known is None:
            continue
        breaking = _on_break(shift)
        pins.append(
            {
                "id": driver.id,
                "name": driver.full_name,
                "lat": known.lat,
                "lng": known.lng,
                "online": _online(driver, on_break=breaking),
                "on_break": breaking,
                "gps_source": SOURCE_LAST_KNOWN,
                "recorded_at": known.recorded_at.isoformat(),
                "accuracy_m": known.accuracy_m,
                "heading": known.heading,
                "h3": known.h3,
            }
        )

    if not pins:
        return [], SOURCE_MISS
    return pins, SOURCE_LAST_KNOWN
