"""Notification realtime hub Redis fanout tests."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

from porterchain_api.notification_engine.realtime import RealtimeHub


class FakeWebSocket:
    def __init__(self) -> None:
        self.accepted = False
        self.sent: list[dict] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)


def test_broadcast_delivers_to_local_connections() -> None:
    async def scenario() -> FakeWebSocket:
        hub = RealtimeHub(channel="test:notifications")
        ws = FakeWebSocket()

        await hub.connect("driver", "driver-1", ws)  # type: ignore[arg-type]
        await hub.broadcast("driver", "driver-1", {"type": "notification"})
        return ws

    ws = asyncio.run(scenario())

    assert ws.accepted is True
    assert ws.sent == [{"type": "notification"}]


def test_pubsub_message_from_other_instance_delivers_locally() -> None:
    async def scenario() -> FakeWebSocket:
        hub = RealtimeHub(channel="test:notifications")
        ws = FakeWebSocket()
        await hub.connect("driver", "driver-1", ws)  # type: ignore[arg-type]

        message = json.dumps(
            {
                "origin": "other-process",
                "local_delivered": True,
                "user_role": "driver",
                "user_id": "driver-1",
                "payload": {"type": "notification", "data": {"id": "n1"}},
            }
        )
        data = json.loads(message)
        await hub._broadcast_local(data["user_role"], data["user_id"], data["payload"])
        return ws

    ws = asyncio.run(scenario())

    assert ws.sent == [{"type": "notification", "data": {"id": "n1"}}]


def test_broadcast_sync_publishes_when_no_event_loop() -> None:
    hub = RealtimeHub(channel="test:notifications")
    redis_client = MagicMock()

    with patch("porterchain_shared.redis_client.get_redis_client", return_value=redis_client):
        hub.broadcast_sync("driver", "driver-1", {"type": "notification"})

    redis_client.publish.assert_called_once()
    channel, raw = redis_client.publish.call_args.args
    assert channel == "test:notifications"
    payload = json.loads(raw)
    assert payload["local_delivered"] is False
    assert payload["user_role"] == "driver"
    assert payload["user_id"] == "driver-1"
    assert payload["payload"] == {"type": "notification"}
