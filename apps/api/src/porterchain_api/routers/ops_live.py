"""Ops Today live WebSocket: driver positions, order changes, exceptions (admin, dispatch_read)."""

from __future__ import annotations

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from porterchain_api.notification_engine.realtime import RealtimeHub
from porterchain_api.platform.ops_live import CHANNEL, ROLE, TOPIC

router = APIRouter(prefix="/v1/admin/operations", tags=["operations"])
ops_live_hub = RealtimeHub(channel=CHANNEL)


def _can_watch_dispatch(admin_user_id: str) -> bool:
    from porterchain_api.admin_engine.ops_live_access import can_watch_dispatch

    return can_watch_dispatch(admin_user_id)


@router.websocket("/live/ws")
async def ops_live_ws(websocket: WebSocket, token: str = Query("")):
    from porterchain_api.notification_engine.principal import resolve_notification_ws_user

    user = await resolve_notification_ws_user(token, portal="admin")
    allowed = bool(user and user.user_role == "admin") and await run_in_threadpool(
        _can_watch_dispatch, user.user_id if user else ""
    )
    if not allowed:
        await websocket.accept()
        await websocket.close(code=4401 if not user else 4403)
        return
    await ops_live_hub.connect(ROLE, TOPIC, websocket)
    try:
        await websocket.send_json({"type": "hello"})
        while True:
            if await websocket.receive_text() == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await ops_live_hub.disconnect(ROLE, TOPIC, websocket)
