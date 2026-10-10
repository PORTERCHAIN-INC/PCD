"""WebSocket hub for in-app notification realtime."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from uuid import uuid4

from fastapi import WebSocket

logger = logging.getLogger(__name__)

CHANNEL = "porterchain:notifications:realtime"
_ONLINE_TTL_SECONDS = 180


def touch_online(role: str, user_id: str, *, seconds: int = _ONLINE_TTL_SECONDS) -> None:
    """Remember that this person has the app open. Used to skip staff email."""
    try:
        from porterchain_shared.redis_client import get_redis_client

        get_redis_client().setex(
            f"porterchain:notifications:online:{role}:{user_id}",
            seconds,
            "1",
        )
    except Exception:
        logger.debug("presence touch failed", exc_info=True)


def anyone_online(role: str) -> bool:
    """True when at least one session for this role has the app open.

    If presence cannot be read, treat the app as occupied so mail is not sent.
    """
    try:
        from porterchain_shared.redis_client import get_redis_client

        client = get_redis_client()
        match = f"porterchain:notifications:online:{role}:*"
        for _ in client.scan_iter(match=match, count=20):
            return True
        return False
    except Exception:  # noqa: BLE001
        return True


class RealtimeHub:
    def __init__(self, *, channel: str = CHANNEL) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()
        self._channel = channel
        self._instance_id = str(uuid4())
        self._redis: Any | None = None
        self._pubsub: Any | None = None
        self._listener_task: asyncio.Task | None = None

    def _key(self, user_role: str, user_id: str) -> str:
        return f"{user_role}:{user_id}"

    async def start(self, redis_url: str | None = None) -> None:
        if self._listener_task and not self._listener_task.done():
            return
        try:
            import redis.asyncio as redis
            from porterchain_shared.config.settings import get_platform_settings

            url = redis_url or get_platform_settings().redis_url
            self._redis = redis.from_url(url, decode_responses=True, max_connections=4)
            await self._redis.ping()
            self._pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
            await self._pubsub.subscribe(self._channel)
            self._listener_task = asyncio.create_task(self._listen(), name="notification-realtime-pubsub")
            logger.info("notification realtime Redis pub/sub enabled")
        except Exception as exc:  # noqa: BLE001
            logger.warning("notification realtime Redis pub/sub disabled: %s", exc)
            await self.stop()

    async def stop(self) -> None:
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None
        if self._pubsub:
            try:
                await self._pubsub.unsubscribe(self._channel)
                await self._pubsub.close()
            except Exception:
                logger.debug("failed to close notification realtime pubsub", exc_info=True)
            self._pubsub = None
        if self._redis:
            try:
                await self._redis.aclose()
            except Exception:
                logger.debug("failed to close notification realtime redis", exc_info=True)
            self._redis = None

    async def connect(self, user_role: str, user_id: str, ws: WebSocket) -> None:
        await ws.accept()
        key = self._key(user_role, user_id)
        async with self._lock:
            self._connections.setdefault(key, set()).add(ws)
        touch_online(user_role, user_id)

    async def disconnect(self, user_role: str, user_id: str, ws: WebSocket) -> None:
        key = self._key(user_role, user_id)
        async with self._lock:
            conns = self._connections.get(key)
            if conns and ws in conns:
                conns.discard(ws)
            if conns is not None and len(conns) == 0:
                self._connections.pop(key, None)

    async def broadcast(self, user_role: str, user_id: str, payload: dict[str, Any]) -> None:
        await self._broadcast_local(user_role, user_id, payload)
        await self._publish(user_role, user_id, payload, local_delivered=True)

    async def _broadcast_local(self, user_role: str, user_id: str, payload: dict[str, Any]) -> None:
        key = self._key(user_role, user_id)
        async with self._lock:
            conns = list(self._connections.get(key, set()))
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(payload)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            await self.disconnect(user_role, user_id, ws)

    async def _publish(
        self,
        user_role: str,
        user_id: str,
        payload: dict[str, Any],
        *,
        local_delivered: bool,
    ) -> None:
        if not self._redis:
            return
        message = self._encode_message(user_role, user_id, payload, local_delivered=local_delivered)
        try:
            await self._redis.publish(self._channel, message)
        except Exception:
            logger.debug("failed to publish notification realtime event", exc_info=True)

    def _publish_sync(
        self,
        user_role: str,
        user_id: str,
        payload: dict[str, Any],
        *,
        local_delivered: bool,
    ) -> None:
        try:
            from porterchain_shared.redis_client import get_redis_client

            get_redis_client().publish(
                self._channel,
                self._encode_message(user_role, user_id, payload, local_delivered=local_delivered),
            )
        except Exception:
            logger.debug("failed to publish notification realtime event from sync context", exc_info=True)

    def _encode_message(
        self,
        user_role: str,
        user_id: str,
        payload: dict[str, Any],
        *,
        local_delivered: bool,
    ) -> str:
        return json.dumps(
            {
                "origin": self._instance_id,
                "local_delivered": local_delivered,
                "user_role": user_role,
                "user_id": user_id,
                "payload": payload,
            },
            separators=(",", ":"),
        )

    async def _listen(self) -> None:
        if not self._pubsub:
            return
        async for message in self._pubsub.listen():
            if message.get("type") != "message":
                continue
            try:
                data = json.loads(message.get("data") or "{}")
                if data.get("origin") == self._instance_id and data.get("local_delivered"):
                    continue
                user_role = str(data["user_role"])
                user_id = str(data["user_id"])
                payload = data["payload"]
                if isinstance(payload, dict):
                    await self._broadcast_local(user_role, user_id, payload)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.debug("invalid notification realtime pubsub message", exc_info=True)

    def broadcast_sync(self, user_role: str, user_id: str, payload: dict[str, Any]) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(user_role, user_id, payload))
        except RuntimeError:
            self._publish_sync(user_role, user_id, payload, local_delivered=False)


realtime_hub = RealtimeHub()
