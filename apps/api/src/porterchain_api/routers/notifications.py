"""User notification API — in-app center, devices, preferences, WebSocket."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from porterchain_api.db import get_db
from porterchain_api.notification_engine.device_service import DeviceService
from porterchain_api.notification_engine.engine import get_notification_engine
from porterchain_api.notification_engine.models import NotificationRecord
from porterchain_api.notification_engine.preference_service import PreferenceService
from porterchain_api.notification_engine.principal import NotificationUser, get_notification_user
from porterchain_api.notification_engine.realtime import realtime_hub
from porterchain_api.schemas_notifications import DeviceRegisterRequest, PreferenceUpdateRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/notifications", tags=["notifications"])

_devices = DeviceService()
_prefs = PreferenceService()
_engine = get_notification_engine()


def _inbox_payload(
    db: Session,
    user: NotificationUser,
    *,
    unread_only: bool = False,
    archived: bool = False,
    limit: int = 50,
) -> dict:
    q = db.query(NotificationRecord).filter(
        NotificationRecord.recipient_type == user.user_role,
        NotificationRecord.recipient_id == user.user_id,
        NotificationRecord.channel == "in_app",
        NotificationRecord.is_archived.is_(archived),
    )
    if unread_only and not archived:
        q = q.filter(NotificationRecord.is_read.is_(False))
    rows = q.order_by(NotificationRecord.created_at.desc()).limit(limit).all()
    unread = (
        db.query(NotificationRecord)
        .filter(
            NotificationRecord.recipient_type == user.user_role,
            NotificationRecord.recipient_id == user.user_id,
            NotificationRecord.channel == "in_app",
            NotificationRecord.is_read.is_(False),
            NotificationRecord.is_archived.is_(False),
        )
        .count()
    )
    return {
        "unread_count": unread,
        "items": [
            {
                "id": r.id,
                "title": r.title,
                "body": r.body,
                "priority": r.priority,
                "category": r.category,
                "deep_link": r.deep_link,
                "is_read": r.is_read,
                "is_archived": r.is_archived,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


@router.post("/devices/register")
def register_device(
    body: DeviceRegisterRequest,
    user: Annotated[NotificationUser, Depends(get_notification_user)],
    db: Session = Depends(get_db),
):
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
    db.commit()
    return {"device_id": device.id, "registered": True}


@router.delete("/devices/{device_id}")
def revoke_device(
    device_id: str,
    user: Annotated[NotificationUser, Depends(get_notification_user)],
    db: Session = Depends(get_db),
):
    if not _devices.revoke(db, device_id, user_role=user.user_role, user_id=user.user_id):
        raise HTTPException(status_code=404, detail="device_not_found")
    db.commit()
    return {"ok": True}


@router.get("/inbox")
def inbox(
    user: Annotated[NotificationUser, Depends(get_notification_user)],
    db: Session = Depends(get_db),
    unread_only: bool = False,
    archived: bool = False,
    limit: int = Query(50, le=200),
):
    return _inbox_payload(db, user, unread_only=unread_only, archived=archived, limit=limit)


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
    if not _engine.mark_read(db, notification_id, user_role=user.user_role, user_id=user.user_id):
        raise HTTPException(status_code=404, detail="notification_not_found")
    db.commit()
    return {"ok": True}


@router.post("/inbox/{notification_id}/archive")
def mark_archive(
    notification_id: str,
    user: Annotated[NotificationUser, Depends(get_notification_user)],
    db: Session = Depends(get_db),
):
    if not _engine.mark_archive(db, notification_id, user_role=user.user_role, user_id=user.user_id):
        raise HTTPException(status_code=404, detail="notification_not_found")
    db.commit()
    return {"ok": True}


@router.post("/inbox/mark-all-read")
def mark_all_read(
    user: Annotated[NotificationUser, Depends(get_notification_user)],
    db: Session = Depends(get_db),
):
    count = _engine.mark_all_read(db, user_role=user.user_role, user_id=user.user_id)
    db.commit()
    return {"ok": True, "marked": count}


@router.get("/preferences")
def get_preferences(
    user: Annotated[NotificationUser, Depends(get_notification_user)],
    db: Session = Depends(get_db),
):
    _prefs.ensure_defaults(db, user_role=user.user_role, user_id=user.user_id)
    db.commit()
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
    db.commit()
    return {
        "category": pref.category,
        "email_enabled": pref.email_enabled,
        "push_enabled": pref.push_enabled,
        "sms_enabled": pref.sms_enabled,
        "in_app_enabled": pref.in_app_enabled,
    }


@router.websocket("/ws")
async def notifications_ws(
    websocket: WebSocket,
    token: str = Query(""),
    org_id: str | None = Query(None, alias="org_id"),
):
    from porterchain_api.notification_engine.principal import resolve_notification_ws_user

    user = await resolve_notification_ws_user(token, org_id=org_id)
    if not user:
        await websocket.close(code=4401)
        return

    await realtime_hub.connect(user.user_role, user.user_id, websocket)
    try:
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await realtime_hub.disconnect(user.user_role, user.user_id, websocket)
