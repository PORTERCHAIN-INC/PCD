"""WebSocket hub for in-app notification realtime."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class RealtimeHub:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    def _key(self, user_role: str, user_id: str) -> str:
        return f"{user_role}:{user_id}"

    async def connect(self, user_role: str, user_id: str, ws: WebSocket) -> None:
        await ws.accept()
        key = self._key(user_role, user_id)
        async with self._lock:
            self._connections.setdefault(key, set()).add(ws)

    async def disconnect(self, user_role: str, user_id: str, ws: WebSocket) -> None:
        key = self._key(user_role, user_id)
        async with self._lock:
            conns = self._connections.get(key)
            if conns and ws in conns:
                conns.discard(ws)
            if conns is not None and len(conns) == 0:
                self._connections.pop(key, None)

    async def broadcast(self, user_role: str, user_id: str, payload: dict[str, Any]) -> None:
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

    def broadcast_sync(self, user_role: str, user_id: str, payload: dict[str, Any]) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(user_role, user_id, payload))
        except RuntimeError:
            logger.debug("no event loop for notification broadcast")


realtime_hub = RealtimeHub()
