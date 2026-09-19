"""When a merchant may cancel — English, not state-machine codes.

Cutoff: after the driver is on the way to pickup, cancel is closed.
That is the existing ORDER_TRANSITIONS rule, stated for the portal.
"""

from __future__ import annotations

from porterchain_api.domain.catalog_labels import order_state_label
from porterchain_api.domain.states import OrderState, can_transition_order

CANCEL_UNTIL_HINT = "You can cancel until the driver is on the way to pickup."

_REFUSAL_BY_STATE: dict[str, str] = {
    OrderState.CANCELLED.value: "This order is already cancelled.",
    OrderState.DRIVER_EN_ROUTE.value: (
        "The driver is on the way to pickup. You cannot cancel now — contact support if you need help."
    ),
    OrderState.AT_PICKUP.value: "The driver is at pickup. You cannot cancel this order.",
    OrderState.PICKED_UP.value: "This order is already picked up. You cannot cancel it.",
    OrderState.IN_TRANSIT.value: "This order is already in transit. You cannot cancel it.",
    OrderState.AT_DESTINATION.value: "This order is at the destination. You cannot cancel it.",
    OrderState.DELIVERED.value: "This order is already delivered.",
    OrderState.POD_COMPLETED.value: "This order is already delivered.",
    OrderState.INVOICED.value: "This order is already invoiced. You cannot cancel it.",
    OrderState.CLOSED.value: "This order is closed. You cannot cancel it.",
    OrderState.DRIVER_REJECTED.value: (
        "This order is waiting for another driver. You cannot cancel it from here — contact support."
    ),
    OrderState.DAMAGED.value: "This order is in a damage review. You cannot cancel it.",
    OrderState.LOST.value: "This order is in a loss review. You cannot cancel it.",
    OrderState.CLAIM_OPEN.value: "This order has an open claim. You cannot cancel it.",
    OrderState.REFUNDED.value: "This order is already refunded.",
    OrderState.RETURN_TO_SENDER.value: "This order is returning to you. You cannot cancel it.",
}

_CODES = {
    "already_cancelled": _REFUSAL_BY_STATE[OrderState.CANCELLED.value],
    "order_not_found": "That order was not found.",
    "order_not_owned": "That order was not found.",
    "cannot_cancel": "This order cannot be cancelled in its current status.",
    "unsupported": "That action is not available.",
}


def cancel_allowed(state: str | None) -> bool:
    raw = str(state or "").strip()
    if not raw:
        return False
    try:
        return can_transition_order(OrderState(raw), OrderState.CANCELLED)
    except ValueError:
        return False


def cancel_refusal_for_state(state: str | None) -> str:
    raw = str(state or "").strip()
    if raw in _REFUSAL_BY_STATE:
        return _REFUSAL_BY_STATE[raw]
    label = order_state_label(raw) if raw else "Unknown"
    return f"This order cannot be cancelled while it is {label.lower()}."


def cancel_rule(state: str | None) -> str:
    if cancel_allowed(state):
        return CANCEL_UNTIL_HINT
    return cancel_refusal_for_state(state)


def assert_merchant_can_cancel(state: str) -> None:
    if state == OrderState.CANCELLED.value:
        raise ValueError("already_cancelled")
    if not cancel_allowed(state):
        raise ValueError(f"cannot_cancel:{state}")


def cancel_error_message(code: str) -> str:
    raw = (code or "").strip()
    if raw in _CODES:
        return _CODES[raw]
    if raw.startswith("cannot_cancel:"):
        return cancel_refusal_for_state(raw.split(":", 1)[1])
    if raw.startswith("Invalid order transition"):
        left = raw.replace("Invalid order transition", "", 1).split("->", 1)[0].strip()
        return cancel_refusal_for_state(left)
    if raw.isupper() and "_" in raw:
        return cancel_refusal_for_state(raw)
    return _CODES["cannot_cancel"]


def bulk_exception_message(exc: BaseException) -> str:
    if isinstance(exc, LookupError):
        return cancel_error_message(str(exc) or "order_not_found")
    if isinstance(exc, PermissionError):
        return cancel_error_message("order_not_owned")
    if isinstance(exc, ValueError):
        return cancel_error_message(str(exc))
    return "Could not update this order."
