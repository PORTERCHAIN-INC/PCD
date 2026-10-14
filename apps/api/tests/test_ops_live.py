"""Ops Today live stream: producers, mapping, WS auth + delivery."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from porterchain_api.platform import ops_live
from porterchain_api.routers import ops_live as ops_router


class FakeRedis:
    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []

    def publish(self, channel: str, msg: str) -> int:
        self.published.append((channel, msg))
        return 1

    def eval(self, *_a, **_k):  # CAS accepted
        return 1


def test_message_for_event_maps_orders_and_exceptions_only() -> None:
    o = ops_live.message_for_event("order.driver_assigned", "order", "o1", {"state": "DRIVER_ASSIGNED"})
    assert o == {"type": "order", "id": "o1", "event": "order.driver_assigned", "state": "DRIVER_ASSIGNED"}
    e = ops_live.message_for_event("exception.opened", "order", "o2", {"order_id": "o2"})
    assert e["type"] == "exception" and e["order_id"] == "o2"
    assert ops_live.message_for_event("lead.created", "lead", "l1", {}) is None
    assert ops_live.message_for_event("payment.succeeded", "order", "o1", {}) is None


def test_gps_fix_publishes_driver_position() -> None:
    from porterchain_api.platform.last_known import write_last_known

    r = FakeRedis()
    stored = write_last_known(driver_id="d1", lat=43.65, lng=-79.38, recorded_at=datetime.now(UTC),
                              heading=90.0, h3="x", client=r)
    assert stored is not None
    (channel, raw), = r.published
    msg = json.loads(raw)
    assert channel == ops_live.CHANNEL and msg["user_role"] == "ops"
    assert msg["payload"]["type"] == "driver" and msg["payload"]["id"] == "d1"
    assert msg["payload"]["lat"] == 43.65 and msg["payload"]["heading"] == 90.0


def test_publish_never_raises() -> None:
    class Broken:
        def publish(self, *_a):
            raise ConnectionError("redis down")

    ops_live.publish_ops_live({"type": "order"}, client=Broken())


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(ops_router.router)
    return app


def test_ws_rejects_missing_or_non_admin(monkeypatch) -> None:
    from porterchain_api.notification_engine import principal

    async def nobody(*_a, **_k):
        return None

    monkeypatch.setattr(principal, "resolve_notification_ws_user", nobody)
    with TestClient(_app()).websocket_connect("/v1/admin/operations/live/ws?token=x") as ws:
        with pytest.raises(Exception):
            ws.receive_json()

    async def driver(*_a, **_k):
        return principal.NotificationUser("driver", "d1")

    monkeypatch.setattr(principal, "resolve_notification_ws_user", driver)
    with TestClient(_app()).websocket_connect("/v1/admin/operations/live/ws?token=x") as ws:
        with pytest.raises(Exception):
            ws.receive_json()


def test_ws_admin_without_dispatch_read_is_refused(monkeypatch) -> None:
    from porterchain_api.notification_engine import principal

    async def admin(*_a, **_k):
        return principal.NotificationUser("admin", "a1")

    monkeypatch.setattr(principal, "resolve_notification_ws_user", admin)
    monkeypatch.setattr(ops_router, "_can_watch_dispatch", lambda _uid: False)
    with TestClient(_app()).websocket_connect("/v1/admin/operations/live/ws?token=x") as ws:
        with pytest.raises(Exception):
            ws.receive_json()


def test_ws_streams_to_dispatch_staff(monkeypatch) -> None:
    from porterchain_api.notification_engine import principal

    async def admin(*_a, **_k):
        return principal.NotificationUser("admin", "a1")

    monkeypatch.setattr(principal, "resolve_notification_ws_user", admin)
    monkeypatch.setattr(ops_router, "_can_watch_dispatch", lambda _uid: True)
    with TestClient(_app()) as client, client.websocket_connect("/v1/admin/operations/live/ws?token=x") as ws:
        assert ws.receive_json() == {"type": "hello"}
        ws.send_text("ping")
        assert ws.receive_json() == {"type": "pong"}
        client.portal.call(ops_router.ops_live_hub._broadcast_local, ops_live.ROLE, ops_live.TOPIC,
                           {"type": "driver", "id": "d1", "lat": 1.0, "lng": 2.0})
        assert ws.receive_json()["id"] == "d1"
