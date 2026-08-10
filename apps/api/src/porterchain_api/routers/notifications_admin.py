"""Admin notification center — /v1/admin/notifications/*"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.notification_admin_service import NotificationAdminService
from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import get_db
from porterchain_api.schemas_notifications import BroadcastRequest, SendTestRequest

router = APIRouter(prefix="/v1/admin/notifications", tags=["notifications-admin"])

_svc = NotificationAdminService()
Ctx = Annotated[AdminContext, Depends(get_admin_context)]


def _guard(ctx: AdminContext, module: str) -> None:
    try:
        require_module(ctx, module)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/dashboard")
def dashboard(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "notifications_read")
    return _svc.dashboard(db)


@router.get("/queue")
def queue(
    ctx: Ctx,
    db: Session = Depends(get_db),
    status: str | None = None,
    channel: str | None = None,
    search: str | None = None,
    limit: int = Query(100, le=500),
) -> list[dict]:
    _guard(ctx, "notifications_read")
    return _svc.list_records(db, status=status or "queued", channel=channel, search=search, limit=limit)


@router.get("/history")
def history(
    ctx: Ctx,
    db: Session = Depends(get_db),
    status: str | None = None,
    channel: str | None = None,
    search: str | None = None,
    limit: int = Query(100, le=500),
) -> list[dict]:
    _guard(ctx, "notifications_read")
    return _svc.list_records(db, status=status, channel=channel, search=search, limit=limit)


@router.get("/failed")
def failed(ctx: Ctx, db: Session = Depends(get_db), limit: int = Query(100, le=500)) -> list[dict]:
    _guard(ctx, "notifications_read")
    return _svc.list_records(db, status="failed", limit=limit) + _svc.list_records(db, status="dead_letter", limit=limit)


@router.get("/templates")
def templates(ctx: Ctx) -> list[dict]:
    _guard(ctx, "notifications_read")
    return _svc.templates_catalog()


@router.get("/devices")
def devices(ctx: Ctx, db: Session = Depends(get_db), limit: int = Query(200, le=1000)) -> list[dict]:
    _guard(ctx, "notifications_read")
    return _svc.list_devices(db, limit=limit)


@router.get("/entity-alerts")
def entity_alerts(
    ctx: Ctx,
    db: Session = Depends(get_db),
    recipient_type: str = Query(..., min_length=1),
    recipient_id: str = Query(..., min_length=1),
    limit: int = Query(15, ge=1, le=50),
) -> dict:
    """Trust strip for Partners entity 360 pages (Wave 3)."""
    _guard(ctx, "notifications_read")
    try:
        return _svc.entity_alerts(
            db, recipient_type=recipient_type, recipient_id=recipient_id, limit=limit
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/retry/{notification_id}")
def retry(notification_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "notifications")
    if not _svc.retry(db, notification_id):
        raise HTTPException(status_code=404, detail="notification_not_retryable")
    return {"ok": True}


@router.post("/broadcast")
def broadcast(body: BroadcastRequest, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "notifications")
    result = _svc.broadcast(
        db,
        recipient_type=body.recipient_type,
        recipient_id=body.recipient_id,
        title=body.title,
        body=body.body,
        channel=body.channel,
    )
    return result


@router.post("/send-test")
def send_test(body: SendTestRequest, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "notifications")
    try:
        return _svc.send_test(
            db,
            template_key=body.template_key,
            channel=body.channel,
            recipient_type=body.recipient_type,
            recipient_id=body.recipient_id or ctx.user.id,
            recipient_address=body.recipient_address or ctx.user.email,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{notification_id}/delivery-logs")
def delivery_logs(
    notification_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200),
) -> list[dict]:
    _guard(ctx, "notifications_read")
    return _svc.delivery_logs(db, notification_id, limit=limit)
