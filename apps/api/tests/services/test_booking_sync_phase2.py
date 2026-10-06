"""The Fleetbase sync queue was removed. Pushing an order does not write a job."""

from porterchain_api.platform.retired_sync import BookingSyncService


def test_push_order_does_not_persist() -> None:
    assert BookingSyncService().push_order(None, None, None) is None
