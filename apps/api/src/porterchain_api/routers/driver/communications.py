"""driver routes — communications."""

from fastapi import Body

from porterchain_api.db import db_transaction
from porterchain_api.routers.driver._deps import (
    Annotated,
    Depends,
    DriverContext,
    HTTPException,
    PushRegisterRequest,
    PushUnregisterRequest,
    Query,
    Session,
    Settings,
    get_db,
    get_driver_context,
    get_settings,
    require_approved_driver,
    router,
    svc,
)


@router.post("/push/register")
def register_push(
    body: PushRegisterRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db)):
    from porterchain_api.notification_engine.device_service import InvalidFcmToken

    with db_transaction(db):
        try:
            result = svc.platform.push.register_device(
                db,
                ctx.driver,
                device_token=body.device_token,
                platform=body.platform)
        except InvalidFcmToken as exc:
            raise HTTPException(status_code=400, detail="fcm_token_invalid") from exc
    return result


@router.post("/push/unregister")
def unregister_push(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    body: PushUnregisterRequest = Body(default_factory=PushUnregisterRequest)):
    """Best-effort revoke on sign-out. Token optional — omit to revoke all driver devices."""
    with db_transaction(db):
        result = svc.platform.push.unregister_device(
            db,
            ctx.driver,
            device_token=body.device_token)
    return result


@router.get("/communications")
def communications_hub(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db)):
    return svc.platform.communications.snapshot(db, ctx.driver)


@router.get("/communications/notifications")
def communications_notifications(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db)):
    return svc.platform.communications.inbox(db, ctx.driver.id)


@router.post("/communications/notifications/{notification_id}/read")
def communications_mark_read(
    notification_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db)):
    with db_transaction(db):
        ok = svc.platform.communications.mark_read(db, ctx.driver.id, notification_id)
        if not ok:
            raise HTTPException(status_code=404, detail="notification_not_found")
    return {"ok": True}


@router.post("/communications/notifications/{notification_id}/archive")
def communications_mark_archive(
    notification_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db)):
    with db_transaction(db):
        ok = svc.platform.communications.mark_archive(db, ctx.driver.id, notification_id)
        if not ok:
            raise HTTPException(status_code=404, detail="notification_not_found")
    return {"ok": True}


@router.post("/communications/notifications/mark-all-read")
def communications_mark_all_read(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db)):
    with db_transaction(db):
        count = svc.platform.communications.mark_all_read(db, ctx.driver.id)
    return {"ok": True, "marked": count}


@router.get("/communications/notifications/history")
def communications_notifications_history(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    limit: int = Query(100, le=500)):
    return svc.platform.communications.inbox(db, ctx.driver.id, limit=limit, archived=True)


@router.get("/communications/offline")
def communications_offline(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db)):
    return svc.platform.offline.status(db, ctx.driver.id)


@router.post("/communications/offline/retry")
def communications_offline_retry(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)):
    require_approved_driver(ctx)
    result = svc.persist(
        db,
        lambda: svc.platform.offline.retry_failed(
            db, ctx.driver, executor=svc.offline_executor(db, settings)
        ))
    return result

