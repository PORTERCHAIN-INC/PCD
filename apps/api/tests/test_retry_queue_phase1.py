"""The Fleetbase retry queue was removed."""

from porterchain_api.platform.retired_sync import RetryQueue


def test_enqueue_does_not_persist() -> None:
    assert (
        RetryQueue.enqueue(
            None,
            direction="outbound",
            kind="order",
            idempotency_key="order:gone",
            payload={},
        )
        is None
    )
    assert RetryQueue.claim_due(None) == []
