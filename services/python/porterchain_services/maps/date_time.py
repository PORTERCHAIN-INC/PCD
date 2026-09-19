"""Valhalla ``date_time`` helpers — peak-hour / departure probes (Phase 6).

Valhalla supports time-dependent costing when tiles include traffic. We attach
``date_time`` only when callers opt in; default routing stays time-agnostic so
quotes and dispatch never silently change. Never invent traffic when Valhalla
rejects the field — caller sees ``date_time_applied=false``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def format_valhalla_date_time(
    when: datetime | str | None,
    *,
    time_type: int = 1,
) -> dict[str, Any] | None:
    """Build Valhalla ``date_time`` object.

    ``time_type``: 0=now, 1=departure, 2=arrival (Valhalla route/matrix docs).
    """
    if when is None:
        return None
    if isinstance(when, datetime):
        # Valhalla expects local-ish ``YYYY-MM-DDTHH:MM`` (no tz suffix).
        value = when.strftime("%Y-%m-%dT%H:%M")
    else:
        text = str(when).strip()
        if not text:
            return None
        # Accept ISO with seconds/Z — strip to minute precision.
        value = text.replace("Z", "")[:16]
        if "T" not in value:
            return None
    return {"type": int(time_type), "value": value}


def attach_date_time(
    body: dict[str, Any],
    when: datetime | str | None,
    *,
    time_type: int = 1,
) -> bool:
    """Mutate Valhalla request body. Returns True when attached."""
    payload = format_valhalla_date_time(when, time_type=time_type)
    if not payload:
        return False
    body["date_time"] = payload
    return True
