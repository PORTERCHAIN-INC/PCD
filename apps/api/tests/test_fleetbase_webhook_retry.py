"""Inbound Fleetbase webhook retry was removed with the sync tables."""

from porterchain_api.platform.retired_sync import WebhookProcessor


def test_webhook_processor_does_not_persist() -> None:
    assert WebhookProcessor().process(None, None, {}) is None
