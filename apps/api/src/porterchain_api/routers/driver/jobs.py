"""driver routes — jobs."""

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
    result = svc.platform.location.record_ping(
        db,
        ctx.driver,
        lat=body.lat,
        lng=body.lng,
        accuracy_m=body.accuracy_m,
        heading=body.heading,
        speed_mps=body.speed_mps,
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
    guard_portal_ready(ctx, settings)
    require_approved_driver(ctx)
    try:
        with db.begin():
            result = svc.platform.jobs.optimize_route(db, ctx.driver)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


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
        with db.begin():
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
    try:
        with db.begin():
            stop = svc.platform.stops.deliverstop_response(
                db,
                ctx.driver,
                stop_id,
                fleetbase_bridge=bridge,
                auto_reoptimize=settings.enable_driver_auto_reoptimize,
            )
        return stop_response(stop)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


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
    bridge = svc.fleetbase_bridge(settings)
    result = svc.platform.stops.report_exception(
        db,
        ctx.driver,
        stop_id,
        exception_type=body.exception_type,
        notes=body.notes,
        fleetbase_bridge=bridge,
    )
    return result


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
        with db.begin():
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
        with db.begin():
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


