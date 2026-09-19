"""Job leg helpers — pickup vs delivery phase and allowed driver actions."""

from __future__ import annotations

from porterchain_api.order_engine.buckets import DELIVERY_LEG, DONE_STATES, PICKUP_LEG

_PICKUP_DONE = frozenset({"PICKED_UP", *DELIVERY_LEG, *DONE_STATES})
_DELIVERY_DONE = frozenset({"DELIVERED", *DONE_STATES})


def current_leg(state: str) -> str:
    s = state.upper()
    if s in _DELIVERY_DONE or s in ("POD_COMPLETED", "INVOICED", "CLOSED"):
        return "completed"
    if s in DELIVERY_LEG:
        return "delivery"
    return "pickup"


def pickup_completed(state: str) -> bool:
    return state.upper() in _PICKUP_DONE


def delivery_completed(state: str) -> bool:
    return state.upper() in _DELIVERY_DONE


def stop_status_for_leg(state: str, stop_type: str) -> str:
    """Per-stop status for route queues and UI (not raw order.state on both stops)."""
    s = state.upper()
    if stop_type == "pickup":
        if s in _PICKUP_DONE:
            return "picked_up"
        if s in PICKUP_LEG:
            return s.lower()
        return "pending"
    if s in _DELIVERY_DONE:
        return "delivered"
    if s in DELIVERY_LEG:
        return s.lower()
    if s in PICKUP_LEG or s in ("BOOKED", "DISPATCH_READY"):
        return "locked"
    return "pending"


def allowed_actions(state: str) -> list[str]:
    s = state.upper()
    leg = current_leg(s)
    if leg == "completed":
        return []
    if leg == "pickup":
        if s == "DRIVER_ASSIGNED":
            return []
        actions: list[str] = []
        if s in ("DRIVER_ACCEPTED", "DRIVER_EN_ROUTE"):
            actions.append("arrive_pickup")
        if s in ("DRIVER_ACCEPTED", "DRIVER_EN_ROUTE", "AT_PICKUP"):
            actions.append("confirm_pickup")
        return actions
    actions = []
    if s in ("PICKED_UP", "IN_TRANSIT"):
        actions.append("arrive_delivery")
    if s in ("PICKED_UP", "IN_TRANSIT", "AT_DESTINATION"):
        actions.append("confirm_delivery")
    return actions
