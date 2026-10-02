"""Super admin driver steps follow the order state."""

from porterchain_api.admin_engine.driver_ops_service import driver_actions_for


def test_assigned_order_can_be_accepted_and_declined() -> None:
    ids = [item["id"] for item in driver_actions_for("DRIVER_ASSIGNED", has_driver=True)]
    assert ids == ["accept", "decline", "start_route"]


def test_picked_up_order_has_delivery_steps_only() -> None:
    ids = [item["id"] for item in driver_actions_for("PICKED_UP", has_driver=True)]
    assert "accept" not in ids
    assert "decline" not in ids
    assert ids == ["start_route", "arrive_delivery", "complete_delivery"]


def test_unassigned_order_has_no_driver_steps() -> None:
    assert driver_actions_for("DRIVER_ASSIGNED", has_driver=False) == []
