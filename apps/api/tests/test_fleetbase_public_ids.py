"""Live Fleetbase public ids vs local placeholder fixtures."""

from porterchain_api.dispatch_engine.public_ids import is_consumable_public_id


def test_live_order_and_vehicle_ids_pass() -> None:
    assert is_consumable_public_id("order_cuoncwg6zt") is True
    assert is_consumable_public_id("vehicle_abc123xyz") is True
    assert is_consumable_public_id("driver_abc123xyz") is True
    assert is_consumable_public_id("6f1c2d3e-4a5b-6c7d-8e9f-0a1b2c3d4e5f") is True


def test_placeholder_and_blank_ids_fail() -> None:
    assert is_consumable_public_id("fb-123") is False
    assert is_consumable_public_id("fb-1") is False
    assert is_consumable_public_id("fb-f430298b") is False
    assert is_consumable_public_id("") is False
    assert is_consumable_public_id(None) is False
    assert is_consumable_public_id("order_") is False
