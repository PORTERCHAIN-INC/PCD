"""driver routes — navigation_pod."""

from porterchain_api.db import db_transaction
from porterchain_api.routers.driver._deps import (
    Annotated,
    Depends,
    DriverContext,
    HTTPException,
    OfflineActionRequest,
    PodBarcodeRequest,
    PodOtpRequest,
    PodPhotoRequest,
    PodSignatureRequest,
    Session,
    Settings,
    get_db,
    get_driver_context,
    get_settings,
    require_approved_driver,
    router,
    svc)


@router.get("/navigation/session")
def navigation_session(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    order_id: str | None = None):
    """Full navigation session — Fleetbase GPS, OSRM ETA, Valhalla route."""
    if not order_id:
        jobs = svc.platform.jobs.list_jobs(db, ctx.driver)
        current = jobs.get("current")
        if not current:
            return svc.platform.navigation.idle_session(ctx.driver)
        order_id = current["order_id"]
    try:
        return svc.platform.navigation.session(
            db, ctx.driver, order_id, settings
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="job_not_found") from exc


@router.get("/navigation/route")
def navigationroute_response(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    route_id: str | None = None):
    if not route_id:
        route = svc.platform.stops.assignedroute_response(db, ctx.driver)
        if not route:
            raise HTTPException(status_code=404, detail="route_not_found")
        route_id = route.route_id
    return svc.platform.navigation.route_session(
        db, ctx.driver, route_id, settings
    )


@router.get("/orders/{order_id}/navigation")
def order_navigation(
    order_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)):
    try:
        return svc.platform.navigation.route_for_order(
            db, ctx.driver, order_id, settings
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="order_not_found") from exc


@router.post("/routes/{route_id}/stops/{stop_id}/pod-photo")
def pod_photo(
    route_id: str,
    stop_id: str,
    body: PodPhotoRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)):
    require_approved_driver(ctx)
    try:
        with db_transaction(db):
            result = svc.platform.pod.capture_photo(
                db,
                ctx.driver,
                stop_id,
                file_url=body.file_url)
        return {"success": result.success}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="stop_not_found") from exc


@router.post("/routes/{route_id}/stops/{stop_id}/pod-signature")
def pod_signature(
    route_id: str,
    stop_id: str,
    body: PodSignatureRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)):
    require_approved_driver(ctx)
    try:
        with db_transaction(db):
            result = svc.platform.pod.capture_signature(
                db,
                ctx.driver,
                stop_id,
                signature_data=body.signature_data)
        return {"success": result.success}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="stop_not_found") from exc


@router.post("/routes/{route_id}/stops/{stop_id}/pod-barcode")
def pod_barcode(
    route_id: str,
    stop_id: str,
    body: PodBarcodeRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)):
    require_approved_driver(ctx)
    try:
        with db_transaction(db):
            result = svc.platform.pod.capture_barcode(
                db,
                ctx.driver,
                stop_id,
                barcode=body.barcode)
        return {"success": result.success}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="stop_not_found") from exc


@router.post("/routes/{route_id}/stops/{stop_id}/pod-complete")
def pod_complete(
    route_id: str,
    stop_id: str,
    body: PodOtpRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)):
    require_approved_driver(ctx)
    try:
        with db_transaction(db):
            result = svc.platform.pod.complete_pod(
                db,
                ctx.driver,
                stop_id,
                otp=body.otp)
            if not result.success:
                raise HTTPException(status_code=400, detail=result.message)
        return {"success": True, "state": "POD_COMPLETED"}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="stop_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/orders/{order_id}/otp")
def generate_otp(
    order_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db)):
    require_approved_driver(ctx)
    try:
        with db_transaction(db):
            otp = svc.platform.pod.generate_otp(db, ctx.driver, order_id)
        return {"otp": otp}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="order_not_found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="order_not_assigned_to_driver") from exc


@router.post("/offline/queue")
def queue_offline(
    body: OfflineActionRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db)):
    with db_transaction(db):
        result = svc.platform.offline.queue_action(
            db,
            ctx.driver,
            action_type=body.action_type,
            payload=body.payload,
            client_id=body.client_id)
    return result


@router.get("/offline/pending")
def offline_pending(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return {"actions": svc.platform.offline.list_pending(db, ctx.driver.id)}


@router.post("/offline/sync")
def offline_sync(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)):
    """Replay queued offline actions through DriverPlatform (connectivity restored)."""
    require_approved_driver(ctx)
    return svc.persist(
        db,
        lambda: svc.platform.offline.sync_pending(
            db, ctx.driver, executor=svc.offline_executor(db, settings)
        ))
