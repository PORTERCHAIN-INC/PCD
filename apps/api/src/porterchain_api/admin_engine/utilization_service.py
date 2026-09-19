"""Shift & utilization snapshot for Control Tower staffing.

Online/availability prefers the Redis Fleetbase ops mirror (worker-refreshed).
Shift duration / break minutes come from Porterchain `driver_shifts` (driver
portal SSOT). Active load is the PC order mirror — never invent GPS math.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Driver
from porterchain_api.driver_models import DriverShift
from porterchain_api.fleetbase_engine import ops_mirror
from porterchain_api.booking_models import Order
from porterchain_api.order_engine.buckets import IN_FLIGHT, WAITING

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    from datetime import timezone

    return datetime.now(timezone.utc)


def _minutes_between(start: datetime | None, end: datetime | None) -> int:
    if not start:
        return 0
    a = start if start.tzinfo else start.replace(tzinfo=_now_utc().tzinfo)
    b = end if end else _now_utc()
    if b.tzinfo is None and a.tzinfo is not None:
        b = b.replace(tzinfo=a.tzinfo)
    secs = max(0, (b - a).total_seconds())
    return int(secs // 60)


class UtilizationService:
    def __init__(self, adapter: Any = None) -> None:
        del adapter  # leftover GET path inverted — mirror only

    def snapshot(self, db: Session) -> dict[str, Any]:
        now = _now_utc()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        drivers = (
            db.query(Driver)
            .filter(Driver.status == "APPROVED")
            .order_by(Driver.full_name.asc())
            .limit(200)
            .all()
        )
        driver_ids = [d.id for d in drivers]

        loads: dict[Any, int] = {}
        shifts: list[DriverShift] = []
        if driver_ids:
            loads = dict(
                db.query(Order.assigned_driver_id, func.count(Order.id))
                .filter(
                    Order.is_sandbox.is_(False),
                    Order.state.in_(IN_FLIGHT),
                    Order.assigned_driver_id.in_(driver_ids),
                )
                .group_by(Order.assigned_driver_id)
                .all()
            )
            shifts = (
                db.query(DriverShift)
                .filter(
                    DriverShift.driver_id.in_(driver_ids),
                    DriverShift.started_at >= day_start - timedelta(hours=12),
                )
                .order_by(DriverShift.started_at.desc())
                .all()
            )

        waiting = (
            db.query(func.count(Order.id))
            .filter(
                Order.is_sandbox.is_(False),
                Order.state.in_(WAITING),
                Order.assigned_driver_id.is_(None),
            )
            .scalar()
            or 0
        )
        active_shift_by_driver: dict[str, DriverShift] = {}
        for s in shifts:
            if s.driver_id in active_shift_by_driver:
                continue
            if s.status in {"active", "on_break", "break"} or s.ended_at is None:
                active_shift_by_driver[s.driver_id] = s

        online_by_fb = ops_mirror.online_map_from_mirror()
        online_source = (
            ops_mirror.SOURCE_MIRROR if online_by_fb else "porterchain_mirror"
        )

        rows: list[dict[str, Any]] = []
        for d in drivers:
            fb_online = (
                online_by_fb.get(d.fleetbase_driver_id)
                if d.fleetbase_driver_id
                else None
            )
            online = (
                fb_online
                if fb_online is not None
                else bool(d.is_online) or d.availability == "online"
            )
            shift = active_shift_by_driver.get(d.id)
            load = int(loads.get(d.id, 0))
            on_break = bool(
                shift
                and (
                    shift.break_started_at is not None
                    or str(shift.status).lower() in {"on_break", "break"}
                )
                and shift.ended_at is None
            )
            on_shift = bool(shift and shift.ended_at is None)
            shift_minutes = _minutes_between(
                shift.started_at if shift else None,
                shift.ended_at if shift else None,
            )
            break_minutes = int(shift.break_minutes) if shift else 0
            if on_break and shift and shift.break_started_at:
                break_minutes += _minutes_between(shift.break_started_at, None)

            if on_break:
                util_status = "on_break"
            elif load > 0:
                util_status = "busy"
            elif on_shift and online:
                util_status = "idle"
            elif online:
                util_status = "available"
            elif on_shift:
                util_status = "on_shift_offline"
            else:
                util_status = "offline"

            # Rough utilization: busy minutes ≈ min(shift, load * 45) heuristic labeled as such
            busy_estimate = min(shift_minutes, load * 45) if on_shift else 0
            util_pct = (
                round(100 * busy_estimate / shift_minutes, 1) if shift_minutes > 0 else 0.0
            )

            rows.append(
                {
                    "id": d.id,
                    "name": d.full_name,
                    "fleetbase_driver_id": d.fleetbase_driver_id,
                    "online": online,
                    "on_shift": on_shift,
                    "on_break": on_break,
                    "active_orders": load,
                    "shift_minutes": shift_minutes,
                    "break_minutes": break_minutes,
                    "status": util_status,
                    "utilization_percent": util_pct,
                    "utilization_note": "estimate_from_load",
                    "rating": d.rating,
                }
            )

        online_n = sum(1 for r in rows if r["online"])
        on_shift_n = sum(1 for r in rows if r["on_shift"])
        idle_n = sum(1 for r in rows if r["status"] == "idle")
        busy_n = sum(1 for r in rows if r["status"] == "busy")
        break_n = sum(1 for r in rows if r["on_break"])
        total_load = sum(r["active_orders"] for r in rows)
        avg_load = round(total_load / online_n, 2) if online_n else 0.0

        rows.sort(
            key=lambda r: (
                0 if r["status"] == "idle" else 1 if r["status"] == "busy" else 2,
                -r["active_orders"],
                r["name"] or "",
            )
        )

        return {
            "as_of": now.isoformat(),
            "online_source": online_source,
            "summary": {
                "drivers_total": len(rows),
                "online": online_n,
                "on_shift": on_shift_n,
                "idle": idle_n,
                "busy": busy_n,
                "on_break": break_n,
                "waiting_unassigned": int(waiting),
                "active_orders": total_load,
                "avg_load_per_online": avg_load,
                "staffing_gap": max(0, int(waiting) - idle_n),
            },
            "drivers": rows,
        }
