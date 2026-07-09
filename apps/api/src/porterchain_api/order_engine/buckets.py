"""Shared order state buckets — used by admin, merchant, route center, reporting."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from porterchain_api.booking_engine.compliance_metadata import delivery_window_end

# Operational order states (control tower).
WAITING = ("DISPATCH_READY",)
PICKUP_LEG = ("DRIVER_ASSIGNED", "DRIVER_ACCEPTED", "DRIVER_EN_ROUTE", "AT_PICKUP")
DELIVERY_LEG = ("PICKED_UP", "IN_TRANSIT", "AT_DESTINATION")
IN_FLIGHT = PICKUP_LEG + DELIVERY_LEG
FAILED_STATES = ("FAILED", "RETURN_TO_SENDER", "LOST", "DAMAGED")
DONE_STATES = ("DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED")

# Unassigned orders eligible for dispatch queue optimization / batch assign.
DISPATCH_POOL = ("BOOKED", "DISPATCH_READY", "DRIVER_REJECTED", "FAILED")
# States where only the delivery stop should be routed (rare unassigned edge case).
DELIVERY_ONLY_POOL = ("PICKED_UP", "IN_TRANSIT", "AT_DESTINATION")

# Merchant dashboard buckets.
ASSIGNED_STATES = ("DRIVER_ASSIGNED", "DRIVER_ACCEPTED", "DRIVER_EN_ROUTE", "AT_PICKUP")
WAITING_DISPATCH = ("BOOKED", "DISPATCH_READY")
PICKED_UP_STATES = ("PICKED_UP", "IN_TRANSIT", "AT_DESTINATION", "DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED")
RETURNED_STATES = ("RETURN_TO_SENDER",)

HIGH_PRIORITY_CENTS = 20000

# Food SLA — orders inside an active delivery window surface first in dispatch (§8.1.8).
FOOD_SLA_DISPATCH_STATES = DISPATCH_POOL + DELIVERY_ONLY_POOL


def dispatch_queue_sort_key(order: Any, *, now: datetime | None = None) -> tuple[int, datetime]:
    """Lower tuple sorts earlier — urgent food windows before generic FIFO."""
    ref = now or datetime.now(UTC)
    window_end = delivery_window_end(getattr(order, "compliance_metadata", None))
    if window_end is not None:
        remaining = (window_end - ref).total_seconds()
        if remaining <= 0:
            return (0, getattr(order, "scheduled_at", ref) or ref)
        if remaining <= 3600:
            return (1, window_end)
    return (2, getattr(order, "scheduled_at", ref) or ref)


BOARD_COLUMNS: list[tuple[str, tuple[str, ...]]] = [
    ("waiting_dispatch", ("BOOKED", "DISPATCH_READY")),
    ("assigned", ("DRIVER_ASSIGNED",)),
    ("accepted", ("DRIVER_ACCEPTED",)),
    ("heading_to_pickup", ("DRIVER_EN_ROUTE",)),
    ("at_pickup", ("AT_PICKUP",)),
    ("picked_up", ("PICKED_UP",)),
    ("in_transit", ("IN_TRANSIT",)),
    ("near_delivery", ("AT_DESTINATION",)),
    ("delivered", ("DELIVERED", "POD_COMPLETED")),
    ("failed", ("FAILED",)),
    ("returned", ("RETURN_TO_SENDER",)),
    ("lost", ("LOST",)),
    ("damaged", ("DAMAGED",)),
]
