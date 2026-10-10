"""Customer and merchant time windows → planner seconds.

Sources, most specific first (all existing booking fields, nothing new to fill in):
- per stop: ``time_window_start`` / ``time_window_end`` on a pickup or drop point
  (admin order builder, multi-stop imports);
- drop: the recipient's chosen slot ``compliance_metadata.cx.schedule``
  (``window_start`` / ``window_end``, self-service reschedule);
- drop: ``compliance_metadata.delivery_window`` (``start`` / ``end``, booking form).

The planner clock starts at plan time (0 s); windows become offsets from it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

Window = tuple[datetime | None, datetime | None]


def _dt(raw: Any) -> datetime | None:
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=UTC)
    if not raw:
        return None
    try:
        d = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def point_window(point: dict[str, Any]) -> Window:
    return _dt(point.get("time_window_start")), _dt(point.get("time_window_end"))


def drop_window(order: Any) -> Window:
    meta = getattr(order, "compliance_metadata", None)
    meta = meta if isinstance(meta, dict) else {}
    cx = meta.get("cx") if isinstance(meta.get("cx"), dict) else {}
    chosen = cx.get("schedule") if isinstance(cx.get("schedule"), dict) else {}
    if chosen.get("window_start") or chosen.get("window_end"):
        return _dt(chosen.get("window_start")), _dt(chosen.get("window_end"))
    booked = meta.get("delivery_window") if isinstance(meta.get("delivery_window"), dict) else {}
    return _dt(booked.get("start")), _dt(booked.get("end"))


def to_offsets(window: Window, origin: datetime) -> tuple[int | None, int | None]:
    """Seconds from ``origin``; a window already over keeps ``end=0`` (late, still served)."""
    start, end = window
    s = None if start is None else max(0, int((start - origin).total_seconds()))
    e = None if end is None else max(0, int((end - origin).total_seconds()))
    if s is not None and e is not None and e < s:
        e = s
    return s, e
