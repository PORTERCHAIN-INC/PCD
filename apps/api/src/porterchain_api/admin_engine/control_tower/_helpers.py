"""Shared constants and pure helpers for the control tower package."""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime

from porterchain_api.domain.states import ORDER_TRANSITIONS, OrderState
from porterchain_api.order_engine.buckets import BOARD_COLUMNS

CARD_CAP = 60

# Canonical order state when an order is dropped on a board column.
BOARD_COLUMN_TARGET: dict[str, str] = {
    "waiting_dispatch": "DISPATCH_READY",
    "assigned": "DRIVER_ASSIGNED",
    "accepted": "DRIVER_ACCEPTED",
    "heading_to_pickup": "DRIVER_EN_ROUTE",
    "at_pickup": "AT_PICKUP",
    "picked_up": "PICKED_UP",
    "in_transit": "IN_TRANSIT",
    "near_delivery": "AT_DESTINATION",
    "delivered": "DELIVERED",
    "failed": "FAILED",
    "returned": "RETURN_TO_SENDER",
    "lost": "LOST",
    "damaged": "DAMAGED",
}

# Execution columns move with driver check-ins. The admin board may only mark
# commercial exceptions; forward progress comes from the driver app.
BOARD_EXECUTION_COLUMNS = frozenset(
    {
        "waiting_dispatch",
        "assigned",
        "accepted",
        "heading_to_pickup",
        "at_pickup",
        "picked_up",
        "in_transit",
        "near_delivery",
        "delivered",
    }
)


def column_for_state(state: str) -> str | None:
    for key, states in BOARD_COLUMNS:
        if state in states:
            return key
    return None


def transition_path(from_state: OrderState, to_state: OrderState) -> list[OrderState] | None:
    if from_state == to_state:
        return []
    queue: deque[tuple[OrderState, list[OrderState]]] = deque([(from_state, [])])
    visited = {from_state}
    while queue:
        current, steps = queue.popleft()
        for nxt in ORDER_TRANSITIONS.get(current, set()):
            if nxt == to_state:
                return steps + [nxt]
            if nxt not in visited:
                visited.add(nxt)
                queue.append((nxt, steps + [nxt]))
    return None


def now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def has_coords(addr: dict | None) -> bool:
    if not addr:
        return False
    lat = addr.get("lat") or addr.get("latitude")
    lng = addr.get("lng") or addr.get("lon") or addr.get("longitude")
    return lat is not None and lng is not None


# Backward-compatible private aliases (used by coverage tests via shim).
_column_for_state = column_for_state
_transition_path = transition_path
_now = now_utc
_has_coords = has_coords
