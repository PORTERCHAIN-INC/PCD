"""Order state machine tests — all valid transitions per ORDER_LIFECYCLE.md (DD-01)."""

from __future__ import annotations

import itertools

import pytest

from porterchain_api.domain.states import ORDER_TRANSITIONS, OrderState, can_transition_order

_TERMINAL_STATES = frozenset(
    {
        OrderState.CLOSED,
        OrderState.CANCELLED,
        OrderState.REFUNDED,
    }
)


def test_same_state_always_allowed() -> None:
    for state in OrderState:
        assert can_transition_order(state, state) is True


@pytest.mark.parametrize(
    ("from_state", "to_state"),
    [
        (from_state, to_state)
        for from_state, targets in ORDER_TRANSITIONS.items()
        for to_state in targets
    ],
)
def test_declared_transitions_are_allowed(from_state: OrderState, to_state: OrderState) -> None:
    assert can_transition_order(from_state, to_state) is True


@pytest.mark.parametrize(
    ("from_state", "to_state"),
    [
        (from_state, to_state)
        for from_state, to_state in itertools.product(OrderState, OrderState)
        if from_state != to_state
        and to_state not in ORDER_TRANSITIONS.get(from_state, set())
    ],
)
def test_undeclared_transitions_are_rejected(from_state: OrderState, to_state: OrderState) -> None:
    assert can_transition_order(from_state, to_state) is False


@pytest.mark.parametrize("terminal", sorted(_TERMINAL_STATES, key=lambda s: s.value))
def test_terminal_states_cannot_move_forward(terminal: OrderState) -> None:
    for target in OrderState:
        if target == terminal:
            continue
        assert can_transition_order(terminal, target) is False


def test_happy_path_delivery_flow() -> None:
    path = [
        OrderState.BOOKED,
        OrderState.DISPATCH_READY,
        OrderState.DRIVER_ASSIGNED,
        OrderState.DRIVER_ACCEPTED,
        OrderState.DRIVER_EN_ROUTE,
        OrderState.AT_PICKUP,
        OrderState.PICKED_UP,
        OrderState.IN_TRANSIT,
        OrderState.AT_DESTINATION,
        OrderState.DELIVERED,
        OrderState.POD_COMPLETED,
        OrderState.INVOICED,
        OrderState.CLOSED,
    ]
    for current, nxt in zip(path, path[1:], strict=False):
        assert can_transition_order(current, nxt) is True


def test_failed_order_can_redispatch() -> None:
    assert can_transition_order(OrderState.FAILED, OrderState.DISPATCH_READY) is True
    assert can_transition_order(OrderState.FAILED, OrderState.RETURN_TO_SENDER) is True
    assert can_transition_order(OrderState.FAILED, OrderState.CANCELLED) is True


def test_driver_rejection_paths() -> None:
    assert can_transition_order(OrderState.DRIVER_REJECTED, OrderState.DRIVER_ASSIGNED) is True
    assert can_transition_order(OrderState.DRIVER_REJECTED, OrderState.DISPATCH_READY) is True
    assert can_transition_order(OrderState.DRIVER_REJECTED, OrderState.DELIVERED) is False


def test_claim_and_refund_paths() -> None:
    assert can_transition_order(OrderState.DAMAGED, OrderState.CLAIM_OPEN) is True
    assert can_transition_order(OrderState.LOST, OrderState.CLAIM_OPEN) is True
    assert can_transition_order(OrderState.CLAIM_OPEN, OrderState.REFUNDED) is True
    assert can_transition_order(OrderState.CLAIM_OPEN, OrderState.CLOSED) is True
