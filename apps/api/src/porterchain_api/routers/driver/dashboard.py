"""driver routes — dashboard."""

from porterchain_api.routers.driver._deps import *  # noqa: F403

@router.get("/dashboard", response_model=DriverDashboardResponse)
def dashboard(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    _guard_portal_ready(ctx, settings)
    snap = _svc.platform.dashboard.snapshot(db, ctx.driver)
    return DriverDashboardResponse(
        todays_earnings_cents=snap.todays_earnings_cents,
        todays_stops_total=snap.todays_stops_total,
        todays_stops_completed=snap.todays_stops_completed,
        wallet_balance_cents=snap.wallet_balance_cents,
        is_online=snap.is_online,
        availability=snap.availability,
        rating=snap.rating,
        active_route_id=snap.active_route_id,
        bonuses_available=snap.bonuses_available,
        performance_score=snap.performance_score,
        pending_documents=snap.pending_documents,
    )


@router.get("/earnings")
def earnings_snapshot(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    return _svc.platform.finance.snapshot(db, ctx.driver)


@router.get("/earnings/today")
def earnings_today(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    snap = _svc.platform.finance.snapshot(db, ctx.driver)
    return {
        "today_cents": snap["today_cents"],
        "week_cents": snap["week_cents"],
        "month_cents": snap["month_cents"],
    }


@router.get("/earnings/statements")
def earnings_statements(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    return {"statements": _svc.platform.finance.list_statements(db, ctx.driver.id)}


@router.get("/earnings/statements/{statement_id}")
def earnings_statement_detail(
    statement_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    try:
        return _svc.platform.finance.statement_detail(db, ctx.driver.id, statement_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/earnings/statements/{statement_id}/download")
def earnings_statement_download(
    statement_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    try:
        content, filename = _svc.platform.finance.statement_csv(db, ctx.driver.id, statement_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/wallet")
def wallet(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return {
        "balance_cents": _svc.platform.wallet.balance_cents(ctx.driver),
        "transactions": [
            {
                "id": t.id,
                "type": t.type,
                "amount_cents": t.amount_cents,
                "balance_after_cents": t.balance_after_cents,
                "description": t.description,
                "reference_id": t.reference_id,
                "created_at": t.created_at.isoformat(),
            }
            for t in _svc.platform.wallet.list_transactions(db, ctx.driver.id)
        ],
        "payouts": _svc.platform.wallet.list_payouts(db, ctx.driver.id),
    }


@router.get("/bonuses")
def bonuses(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return {"bonuses": _svc.platform.bonuses.list_bonuses(db, ctx.driver.id)}


@router.post("/bonuses/{bonus_id}/claim")
def claim_bonus(
    bonus_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    try:
        result = _svc.platform.bonuses.claim_bonus(db, ctx.driver, bonus_id)
        db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="bonus_not_found") from exc


@router.get("/performance")
def performance(ctx: Annotated[DriverContext, Depends(get_driver_context)]):
    return _svc.platform.performance.summary(ctx.driver)


@router.get("/ratings")
def ratings(ctx: Annotated[DriverContext, Depends(get_driver_context)]):
    return _svc.platform.ratings.summary(ctx.driver)


@router.post("/availability")
def set_availability(
    body: AvailabilityRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = _svc.fleetbase_bridge(settings)
    if body.mode is None and body.online is None:
        raise HTTPException(status_code=422, detail="online or mode required")
    try:
        if body.mode is not None:
            result = _svc.platform.shift.set_availability(
                db, ctx.driver, body.mode, fleetbase_bridge=bridge
            )
        else:
            mode = "online" if body.online else "offline"
            result = _svc.platform.shift.set_availability(
                db, ctx.driver, mode, fleetbase_bridge=bridge
            )
        db.commit()
        return result
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/shift")
def get_shift(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    return _svc.platform.shift.snapshot(db, ctx.driver)


@router.post("/shift/start")
def start_shift(
    body: ShiftStartRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = _svc.fleetbase_bridge(settings)
    try:
        result = _svc.platform.shift.start_shift(
            db, ctx.driver, fleetbase_bridge=bridge, route_id=body.route_id
        )
        db.commit()
        return result
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/shift/end")
def end_shift(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = _svc.fleetbase_bridge(settings)
    try:
        result = _svc.platform.shift.end_shift(db, ctx.driver, fleetbase_bridge=bridge)
        db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/shift/break")
def shift_break(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = _svc.fleetbase_bridge(settings)
    try:
        result = _svc.platform.shift.start_break(db, ctx.driver, fleetbase_bridge=bridge)
        db.commit()
        return result
    except (LookupError, PermissionError) as exc:
        code = 404 if isinstance(exc, LookupError) else 403
        raise HTTPException(status_code=code, detail=str(exc)) from exc


@router.post("/shift/resume")
def shift_resume(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = _svc.fleetbase_bridge(settings)
    try:
        result = _svc.platform.shift.resume_shift(db, ctx.driver, fleetbase_bridge=bridge)
        db.commit()
        return result
    except (LookupError, PermissionError) as exc:
        code = 404 if isinstance(exc, LookupError) else 403
        raise HTTPException(status_code=code, detail=str(exc)) from exc


