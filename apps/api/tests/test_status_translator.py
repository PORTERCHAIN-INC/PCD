"""Fleetbase status translation tests."""

from porterchain_api.domain.states import OrderState
from porterchain_api.domain.status_translator import StatusTranslator


def test_completed_maps_to_delivered() -> None:
    assert StatusTranslator.to_state(status="completed") == OrderState.DELIVERED


def test_picked_up_event() -> None:
    assert StatusTranslator.to_state(event="order.picked_up") == OrderState.PICKED_UP


def test_classify_tracking_event() -> None:
    assert StatusTranslator.classify("order.tracking") == "tracking"
