"""Driver check-in timestamps per order (arrived / picked_up / delivered / failed).

Shared read for billing evidence (waiting time, failed delivery) without billing
importing dispatch internals.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def stop_events_by_order(db: Any, order_ids: list[str]) -> dict[str, list[tuple[str, str, datetime]]]:
    from porterchain_api.dispatch_engine.models import DispatchStopEvent

    out: dict[str, list[tuple[str, str, datetime]]] = {}
    if not order_ids:
        return out
    rows = (
        db.query(DispatchStopEvent.order_id, DispatchStopEvent.stop_key, DispatchStopEvent.event, DispatchStopEvent.at)
        .filter(DispatchStopEvent.order_id.in_(order_ids))
        .all()
    )
    for oid, key, ev, at in rows:
        out.setdefault(oid, []).append((key, ev, at))
    return out
