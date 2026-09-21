"""driver routes — jobs."""

from porterchain_api.db import db_transaction
from porterchain_api.routers.driver._deps import (
    AcceptRejectRequest,
    Annotated,
    Depends,
    DriverContext,
    DriverJobDetailResponse,
    DriverJobsListResponse,
    DriverJobsOptimizeResponse,
    ExceptionRequest,
    HTTPException,
    LocationPingRequest,
    RouteResponse,
    Session,
    Settings,
    get_db,
    get_driver_context,
    get_settings,
    guard_portal_ready,
    require_approved_driver,
    route_response,
    router,
    stop_response,
    svc,
)


@router.post("/location")
def location_ping(
    body: LocationPingRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = svc.fleetbase_bridge(settings)
    with db_transaction(db):
        result = svc.platform.location.record_ping(
            db,
            ctx.driver,
            lat=body.lat,
            lng=body.lng,
            accuracy_m=body.accuracy_m,
            heading=body.heading,
            speed_mps=body.speed_mps,
            recorded_at=body.recorded_at,
            write_ping_table=settings.gps_write_ping_table,
            fleetbase_bridge=bridge,
        )
    return result


@router.get("/jobs", response_model=DriverJobsListResponse)
def list_jobs(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    guard_portal_ready(ctx, settings)
    return svc.platform.jobs.list_jobs(db, ctx.driver)


@router.post("/jobs/optimize", response_model=DriverJobsOptimizeResponse)
def optimize_jobs(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Queue Fleetbase VROOM preview — does not apply until Accept."""
    guard_portal_ready(ctx, settings)
    require_approved_driver(ctx)
    try:
        with db_transaction(db):
            result = svc.platform.jobs.optimize_route(db, ctx.driver, preview=True)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/jobs/optimize/runs/{run_id}", response_model=DriverJobsOptimizeResponse)
def optimize_jobs_status(
    run_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    expected_version: int | None = None,
    apply: bool = False,
):
    """Poll preview status. Pass apply=true only from Accept (or legacy clients)."""
    guard_portal_ready(ctx, settings)
    require_approved_driver(ctx)
    from porterchain_driver.sequence_store import SequenceConflictError

    try:
        return svc.platform.jobs.optimize_run_status(
            db,
            ctx.driver,
            run_id,
            expected_version=expected_version,
            apply=apply,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="optimize_run_not_found") from exc
    except SequenceConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "sequence_version_conflict",
                "current_version": exc.current_version,
                "expected_version": exc.expected_version,
            },
        ) from exc


@router.post("/jobs/optimize/runs/{run_id}/accept", response_model=DriverJobsOptimizeResponse)
def optimize_jobs_accept(
    run_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    expected_version: int | None = None,
):
    """Apply a ready preview to this driver's stop sequence."""
    guard_portal_ready(ctx, settings)
    require_approved_driver(ctx)
    from porterchain_driver.sequence_store import SequenceConflictError

    try:
        return svc.platform.jobs.accept_optimize_run(
            db, ctx.driver, run_id, expected_version=expected_version
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="optimize_run_not_found") from exc
    except SequenceConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "sequence_version_conflict",
                "current_version": exc.current_version,
                "expected_version": exc.expected_version,
            },
        ) from exc


@router.post("/jobs/optimize/undo", response_model=DriverJobsOptimizeResponse)
def optimize_jobs_undo(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Restore the previous stop sequence after Accept."""
    guard_portal_ready(ctx, settings)
    require_approved_driver(ctx)
    return svc.platform.jobs.undo_optimize(db, ctx.driver)


@router.get("/jobs/history")
def jobs_history(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    guard_portal_ready(ctx, settings)
    return {"history": svc.platform.jobs.order_history(db, ctx.driver)}


@router.get("/jobs/{order_id}", response_model=DriverJobDetailResponse)
def job_detail(
    order_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    guard_portal_ready(ctx, settings)
    try:
        return svc.platform.jobs.job_detail(db, ctx.driver, order_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="job_not_found") from exc


@router.get("/routes/assigned", response_model=RouteResponse | None)
def assignedroute_response(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    route = svc.platform.stops.assignedroute_response(db, ctx.driver)
    if not route:
        return None
    return route_response(route)


@router.post("/routes/{route_id}/start", response_model=RouteResponse)
def startroute_response(
    route_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = svc.fleetbase_bridge(settings)
    route = svc.platform.stops.startroute_response(db, ctx.driver, route_id, fleetbase_bridge=bridge)
    return route_response(route)


@router.get("/routes/{route_id}/stops")
def route_stops(
    route_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    stops = svc.platform.stops.stops_forroute_response(db, ctx.driver.id, route_id)
    bridge = svc.fleetbase_bridge(settings)
    nav = svc.platform.navigation.route_for_stops(db, ctx.driver, route_id, settings, fleetbase_bridge=bridge)
    return {"stops": [stop_response(s) for s in stops], "route_polyline": nav.get("route_polyline")}


@router.get("/routes/{route_id}/earnings")
def route_earnings(
    route_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    return {"earnings_cents": svc.platform.earnings.route_earnings_cents(db, ctx.driver.id, route_id)}


@router.post("/routes/{route_id}/stops/{stop_id}/arrive")
def arrivestop_response(
    route_id: str,
    stop_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = svc.fleetbase_bridge(settings)
    try:
        with db_transaction(db):
            stop = svc.platform.stops.arrivestop_response(
                db, ctx.driver, stop_id, fleetbase_bridge=bridge
            )
        return stop_response(stop)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/routes/{route_id}/stops/{stop_id}/deliver")
def deliverstop_response(
    route_id: str,
    stop_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = svc.fleetbase_bridge(settings)
    from porterchain_api.merchant_engine.scan_gate_service import PackagesIncomplete

    try:
        with db_transaction(db):
            stop = svc.platform.stops.deliverstop_response(
                db,
                ctx.driver,
                stop_id,
                fleetbase_bridge=bridge,
                auto_reoptimize=settings.enable_driver_auto_reoptimize,
            )
        return stop_response(stop)
    except PackagesIncomplete as exc:
        raise HTTPException(status_code=409, detail=exc.payload) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/orders/{order_id}/packages/scan")
def scan_order_package(
    order_id: str,
    body: dict,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    """Scan LOGISTICSv1 QR — advances package status for pickup or delivery phase."""
    require_approved_driver(ctx)
    from porterchain_api.merchant_engine.scan_gate_service import (
        PackagesIncomplete,
        ScanGateService,
    )

    try:
        order = svc.require_assigned_order(db, driver_id=ctx.driver.id, order_id=order_id)
        return ScanGateService().scan_qr_from_body(db, order, body, actor_id=ctx.driver.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PackagesIncomplete as exc:
        raise HTTPException(status_code=409, detail=exc.payload) from exc


@router.post("/routes/{route_id}/stops/{stop_id}/exception")
def stop_exception(
    route_id: str,
    stop_id: str,
    body: ExceptionRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    try:
        with db_transaction(db):
            return svc.platform.stops.report_exception(
                db, ctx.driver, stop_id,
                exception_type=body.exception_type, notes=body.notes, photo_url=body.photo_url,
                fleetbase_bridge=svc.fleetbase_bridge(settings),
                auto_reoptimize=settings.enable_driver_auto_reoptimize,
            )
    except (LookupError, ValueError) as exc:
        code = 404 if isinstance(exc, LookupError) else 422
        raise HTTPException(status_code=code, detail=str(exc)) from exc


@router.post("/orders/{order_id}/accept")
def accept_order(
    order_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = svc.fleetbase_bridge(settings)
    try:
        with db_transaction(db):
            result = svc.platform.availability.accept_assignment(
                db, ctx.driver, order_id, fleetbase_bridge=bridge
            )
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="order_not_found") from exc


@router.post("/orders/{order_id}/reject")
def reject_order(
    order_id: str,
    body: AcceptRejectRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = svc.fleetbase_bridge(settings)
    try:
        with db_transaction(db):
            result = svc.platform.availability.reject_assignment(
                db,
                ctx.driver,
                order_id,
                reason=body.reason or "",
                fleetbase_bridge=bridge,
            )
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="order_not_found") from exc


@router.post("/orders/{order_id}/cod-checkout")
def issue_cod_checkout(
    order_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Issue Stripe Checkout Payment Link for COD at the door (Connect destination)."""
    require_approved_driver(ctx)
    from porterchain_api.billing_engine.stripe_cod_service import StripeCodService
    from porterchain_api.merchant_engine.scan_gate_service import PackagesIncomplete

    try:
        order = svc.require_assigned_order(db, driver_id=ctx.driver.id, order_id=order_id)
        return StripeCodService().issue_cod_checkout_for_order(db, settings, order)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except PackagesIncomplete as exc:
        raise HTTPException(status_code=409, detail=exc.payload) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


