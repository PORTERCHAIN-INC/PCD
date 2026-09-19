"""Cancel is idempotent on Fleetbase 404 (seed / already-deleted orders)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from porterchain_fleetbase_adapter.errors import FleetbaseApiError
from porterchain_fleetbase_adapter.orders import OrderService


def test_cancel_treats_404_on_cancel_path_as_success() -> None:
    client = MagicMock()
    client.delete.side_effect = FleetbaseApiError("missing", status_code=404, body="nf")
    svc = OrderService(settings=MagicMock(), client=client)
    assert svc.cancel("fb-123") is True
    client.delete.assert_called_once()


def test_cancel_treats_404_on_delete_fallback_as_success() -> None:
    client = MagicMock()
    client.delete.side_effect = [
        FleetbaseApiError("fail", status_code=500, body="x"),
        FleetbaseApiError("missing", status_code=404, body="nf"),
    ]
    svc = OrderService(settings=MagicMock(), client=client)
    assert svc.cancel("fb-123") is True
    assert client.delete.call_count == 2


def test_cancel_still_false_on_non_404() -> None:
    client = MagicMock()
    client.delete.side_effect = [
        FleetbaseApiError("fail", status_code=500, body="x"),
        FleetbaseApiError("fail", status_code=500, body="x"),
    ]
    svc = OrderService(settings=MagicMock(), client=client, error_handler=MagicMock())
    assert svc.cancel("fb-123") is False
