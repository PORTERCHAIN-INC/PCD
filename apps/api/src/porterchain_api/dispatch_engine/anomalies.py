"""Ops anomalies for the Exceptions queue: stuck orders and idle drivers. Pure, no DB.

- stuck: an active order whose state has not moved for longer than its state allows;
- idle:  an online driver with no active job while an order waits for a driver.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

# Minutes a state may sit before it counts as stuck.
STUCK_MIN = {
    "DRIVER_ASSIGNED": 20,  # offer not accepted
    "DRIVER_ACCEPTED": 45,  # accepted, never left
    "DRIVER_EN_ROUTE": 60,
    "AT_PICKUP": 30,
    "PICKED_UP": 120,
    "IN_TRANSIT": 120,
    "AT_DESTINATION": 30,
}


def _age_min(ts: datetime | None, now: datetime) -> int | None:
    if ts is None:
        return None
    ts = ts if ts.tzinfo else ts.replace(tzinfo=UTC)
    return max(int((now - ts).total_seconds() // 60), 0)


def stuck_items(orders: list[Any], now: datetime) -> list[dict[str, Any]]:
    """Orders past their state's limit, as queue items (``kind='stuck'``)."""
    out = []
    for o in orders:
        limit, age = STUCK_MIN.get(o.state), _age_min(o.updated_at, now)
        if limit is None or age is None or age < limit:
            continue
        out.append({
            "id": f"stuck:{o.id}", "kind": "stuck", "type": "STUCK", "severity": "high",
            "order_id": o.id, "order_number": o.order_number, "state": o.state, "age_min": age,
            "status": "open", "driver_id": o.assigned_driver_id, "limit_min": limit,
        })
    return out


def idle_items(idle_drivers: list[Any], waiting: list[Any], now: datetime) -> list[dict[str, Any]]:
    """Pair each idle driver with the oldest waiting order (``kind='idle'``), oldest first."""
    queue = sorted(waiting, key=lambda o: _age_min(o.created_at, now) or 0, reverse=True)
    return [{
        "id": f"idle:{d.id}", "kind": "idle", "type": "IDLE_DRIVER", "severity": "medium",
        "order_id": o.id, "order_number": o.order_number, "state": o.state,
        "age_min": _age_min(o.created_at, now), "status": "open",
        "idle_driver_id": d.id, "idle_driver_name": d.full_name,
    } for d, o in zip(idle_drivers, queue, strict=False)]
