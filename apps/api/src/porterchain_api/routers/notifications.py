"""User notification API — in-app center, devices, preferences, WebSocket."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from porterchain_api.db import get_db, db_transaction
from porterchain_api.notification_engine.device_service import DeviceService, InvalidFcmToken
from porterchain_api.notification_engine.engine import get_notification_engine
from porterchain_api.notification_engine.preference_service import PreferenceService
from porterchain_api.notification_engine.principal import NotificationUser, get_notification_user
from porterchain_api.notification_engine.realtime import realtime_hub, touch_online
from porterchain_api.notification_engine.user_settings import UserSettingsService
from porterchain_api.schemas_notifications import (
    DeviceRegisterRequest,
    PreferenceUpdateRequest,
    QuietHoursUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/notifications", tags=["notifications"])

_devices = DeviceService()
_prefs = PreferenceService()
_user_settings = UserSettingsService()
_engine = get_notification_engine()


_NOTIF_ERRORS = {
    "notification_not_found": "That notification was not found.",
    "device_not_found": "That device was not found.",
}


def _inbox_payload(
    db: Session,
    user: NotificationUser,
    *,
    unread_only: bool = False,
    archived: bool = False,
    limit: int = 50,
    exclude_templates: set[str] | None = None,
) -> dict:
    payload = _engine.inbox_payload(
        db,
        user_role=user.user_role,
        user_id=user.user_id,
        unread_only=unread_only,
        archived=archived,
        limit=limit,
        exclude_templates=exclude_templates,
    )
    if user.user_role == "merchant":
        payload["merchant_id"] = user.user_id
    return payload


@router.post("/devices/register")
def register_device(
    body: DeviceRegisterRequest,
    user: Annotated[NotificationUser, Depends(get_notification_user)],
    db: Session = Depends(get_db),
):
    with db_transaction(db):
        try:
            device = _devices.register(
                db,
                user_role=user.user_role,
                user_id=user.user_id,
                fcm_token=body.fcm_token,
                platform=body.platform,
                device_name=body.device_name,
                app_version=body.app_version,
                os_version=body.os_version,
                language=body.language,
                timezone=body.timezone,
                notification_permission=body.notification_permission,
            )
        except InvalidFcmToken as exc:
            raise HTTPException(status_code=400, detail="fcm_token_invalid") from exc
    return {"device_id": device.id, "registered": True}


@router.delete("/devices/{device_id}")
def revoke_device(
    device_id: str,
    user: Annotated[NotificationUser, Depends(get_notification_user)],
    db: Session = Depends(get_db),
):
    with db_transaction(db):
        ok = _devices.revoke(db, device_id, user_role=user.user_role, user_id=user.user_id)
        if not ok:
            raise HTTPException(status_code=404, detail=_NOTIF_ERRORS["device_not_found"])
    return {"ok": True}


@router.get("/inbox")
def inbox(
    user: Annotated[NotificationUser, Depends(get_notification_user)],
    db: Session = Depends(get_db),
    unread_only: bool = False,
    archived: bool = False,
    limit: int = Query(50, le=200),
    exclude: str = Query(""),
):
    if user.user_role == "admin":
        touch_online("admin", user.user_id)
    hidden = {part.strip() for part in exclude.split(",") if part.strip()}
    return _inbox_payload(
        db,
        user,
        unread_only=unread_only,
        archived=archived,
        limit=limit,
        exclude_templates=hidden,
    )


@router.get("/inbox/history")
def inbox_history(
    user: Annotated[NotificationUser, Depends(get_notification_user)],
    db: Session = Depends(get_db),
    limit: int = Query(100, le=500),
):
    return _inbox_payload(db, user, archived=True, limit=limit)


@router.post("/inbox/{notification_id}/read")
def mark_read(
    notification_id: str,
    user: Annotated[NotificationUser, Depends(get_notification_user)],
    db: Session = Depends(get_db),
):
    with db_transaction(db):
        ok = _engine.mark_read(db, notification_id, user_role=user.user_role, user_id=user.user_id)
        if not ok:
            raise HTTPException(status_code=404, detail=_NOTIF_ERRORS["notification_not_found"])
    return {"ok": True}


@router.post("/inbox/{notification_id}/archive")
def mark_archive(
    notification_id: str,
    user: Annotated[NotificationUser, Depends(get_notification_user)],
    db: Session = Depends(get_db),
):
    with db_transaction(db):
        ok = _engine.mark_archive(db, notification_id, user_role=user.user_role, user_id=user.user_id)
        if not ok:
            raise HTTPException(status_code=404, detail=_NOTIF_ERRORS["notification_not_found"])
    return {"ok": True}


@router.post("/inbox/mark-all-read")
def mark_all_read(
    user: Annotated[NotificationUser, Depends(get_notification_user)],
    db: Session = Depends(get_db),
):
    with db_transaction(db):
        count = _engine.mark_all_read(db, user_role=user.user_role, user_id=user.user_id)
    return {"ok": True, "marked": count}


@router.get("/preferences")
def get_preferences(
    user: Annotated[NotificationUser, Depends(get_notification_user)],
    db: Session = Depends(get_db),
):
    with db_transaction(db):
        _prefs.ensure_defaults(db, user_role=user.user_role, user_id=user.user_id)
        rows = _prefs.get_all(db, user_role=user.user_role, user_id=user.user_id)
    return [
        {
            "category": p.category,
            "email_enabled": p.email_enabled,
            "push_enabled": p.push_enabled,
            "sms_enabled": p.sms_enabled,
            "in_app_enabled": p.in_app_enabled,
        }
        for p in rows
    ]


@router.patch("/preferences")
def update_preference(
    body: PreferenceUpdateRequest,
    user: Annotated[NotificationUser, Depends(get_notification_user)],
    db: Session = Depends(get_db),
):
    with db_transaction(db):
        pref = _prefs.upsert(
            db,
            user_role=user.user_role,
            user_id=user.user_id,
            category=body.category,
            email_enabled=body.email_enabled,
            push_enabled=body.push_enabled,
            sms_enabled=body.sms_enabled,
            in_app_enabled=body.in_app_enabled,
        )
    return {
        "category": pref.category,
        "email_enabled": pref.email_enabled,
        "push_enabled": pref.push_enabled,
        "sms_enabled": pref.sms_enabled,
        "in_app_enabled": pref.in_app_enabled,
    }


@router.get("/settings")
def get_user_settings(
    user: Annotated[NotificationUser, Depends(get_notification_user)],
    db: Session = Depends(get_db),
):
    tz = _user_settings.resolve_timezone(db, user_role=user.user_role, user_id=user.user_id)
    row = _user_settings.get(db, user_role=user.user_role, user_id=user.user_id)
    return _user_settings.to_dict(row, timezone_fallback=tz)


@router.patch("/settings")
def update_user_settings(
    body: QuietHoursUpdateRequest,
    user: Annotated[NotificationUser, Depends(get_notification_user)],
    db: Session = Depends(get_db),
):
    with db_transaction(db):
        row = _user_settings.upsert(
            db,
            user_role=user.user_role,
            user_id=user.user_id,
            quiet_hours_enabled=body.quiet_hours_enabled,
            quiet_start_hour=body.quiet_start_hour,
            quiet_end_hour=body.quiet_end_hour,
            timezone=body.timezone,
        )
        tz = _user_settings.resolve_timezone(db, user_role=user.user_role, user_id=user.user_id)
    return _user_settings.to_dict(row, timezone_fallback=tz)


@router.websocket("/ws")
async def notifications_ws(
    websocket: WebSocket,
    token: str = Query(""),
    merchant_id: str | None = Query(None),
    portal: str | None = Query(None),
):
    from porterchain_api.notification_engine.principal import resolve_notification_ws_user

    # merchant_id is the websocket twin of X-Merchant-Id — no second selector (BF).
    user = await resolve_notification_ws_user(token, merchant_id=merchant_id, portal=portal)
    if not user:
        # Accept then close — Starlette maps close-before-accept to HTTP 403.
        await websocket.accept()
        await websocket.close(code=4401)
        return

    await realtime_hub.connect(user.user_role, user.user_id, websocket)
    try:
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                if user.user_role == "admin":
                    touch_online("admin", user.user_id)
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await realtime_hub.disconnect(user.user_role, user.user_id, websocket)
