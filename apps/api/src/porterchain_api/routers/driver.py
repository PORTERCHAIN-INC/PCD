"""Driver platform API — /driver-api/v1/* extends Fleetbase capabilities."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from porterchain_api.auth.driver import get_driver_context
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.driver_engine.rbac import (
    DriverContext,
    evaluate_driver_onboarding,
    require_approved_driver,
)
from porterchain_api.schemas_driver import (
    AcceptRejectRequest,
    AvailabilityRequest,
    DocumentUploadRequest,
    DriverClaimOpenRequest,
    DriverDashboardResponse,
    DriverJobDetailResponse,
    DriverJobsListResponse,
    DriverJobsOptimizeResponse,
    DriverLoginRequest,
    DriverOnboardingResponse,
    DriverProfileResponse,
    DriverRefreshRequest,
    DriverTokenResponse,
    EmergencyRequest,
    EmergencyContactUpdateRequest,
    ExceptionRequest,
    IncidentRequest,
    LocationPingRequest,
    OfflineActionRequest,
    PodBarcodeRequest,
    PodOtpRequest,
    PodPhotoRequest,
    PodSignatureRequest,
    PushRegisterRequest,
    RouteResponse,
    ShiftStartRequest,
    StopResponse,
    SupportTicketRequest,
)
from porterchain_api.driver_engine.api_service import DriverApiService
from porterchain_api.driver_engine.mappers import driver_profile, guard_portal_ready, route_response, stop_response

router = APIRouter(prefix="/driver-api/v1", tags=["driver"])
_svc = DriverApiService()


def _guard_portal_ready(ctx: DriverContext, settings: Settings) -> None:
    try:
        guard_portal_ready(ctx, settings)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/auth/login", response_model=DriverTokenResponse)
async def driver_login(
    body: DriverLoginRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
):
    """Driver JWT login — requires Clerk bearer token in production."""
    clerk_token: str | None = None
    if authorization and authorization.startswith("Bearer "):
        clerk_token = authorization.removeprefix("Bearer ").strip()
    try:
        driver, tokens = await _svc.auth.login(
            db, settings, email=body.email, clerk_bearer_token=clerk_token
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="driver_not_found") from None
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return DriverTokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in_seconds,
        driver_id=driver.id,
    )


@router.post("/auth/refresh", response_model=DriverTokenResponse)
def driver_refresh(
    body: DriverRefreshRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        driver, tokens = _svc.auth.refresh(db, settings, refresh_token=body.refresh_token)
    except LookupError:
        raise HTTPException(status_code=404, detail="driver_not_found") from None
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return DriverTokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in_seconds,
        driver_id=driver.id,
    )


@router.get("/me", response_model=DriverProfileResponse)
def driver_me(ctx: Annotated[DriverContext, Depends(get_driver_context)]):
    return driver_profile(ctx.driver)


@router.get("/onboarding", response_model=DriverOnboardingResponse)
def driver_onboarding(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    settings: Settings = Depends(get_settings),
):
    """Onboarding checklist — portal blocks until ready."""
    return DriverOnboardingResponse(**evaluate_driver_onboarding(ctx.driver, settings=settings))


@router.get("/profile")
def driverdriver_profile(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    return _svc.platform.profile.snapshot(db, ctx.driver)


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


@router.get("/vehicle")
def get_vehicle(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return {"vehicle": _svc.platform.vehicle.get_active_vehicle(db, ctx.driver.id), "vehicles": _svc.platform.vehicle.list_vehicles(db, ctx.driver.id)}


@router.get("/insurance")
def insurance(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return _svc.platform.insurance.status(db, ctx.driver)


@router.get("/documents")
def list_documents(ctx: Annotated[DriverContext, Depends(get_driver_context)]):
    return {"documents": _svc.platform.documents.list_documents(ctx.driver)}


@router.post("/documents")
def upload_document(
    body: DocumentUploadRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    try:
        doc = _svc.platform.documents.upload_document(
            db, ctx.driver, doc_type=body.doc_type, file_url=body.file_url, metadata=body.metadata
        )
        db.commit()
        return doc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/profile/vehicle-photos")
def upload_vehicle_photo(
    body: DocumentUploadRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    photo = _svc.platform.documents.upload_vehicle_photo(
        db, ctx.driver, file_url=body.file_url, metadata=body.metadata
    )
    db.commit()
    return photo


@router.get("/training")
def training(ctx: Annotated[DriverContext, Depends(get_driver_context)]):
    return {"modules": _svc.platform.training.list_modules(ctx.driver)}


@router.post("/training/{module_id}/complete")
def complete_training(
    module_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    result = _svc.platform.training.complete_module(db, ctx.driver, module_id)
    db.commit()
    return result


@router.get("/support")
def list_support(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return {"tickets": _svc.platform.support_hub.list_tickets(db, ctx.driver.id)}


@router.get("/support/hub")
def support_hub(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    return _svc.platform.support_hub.snapshot(db, ctx.driver)


@router.get("/support/knowledge-base")
def support_knowledge_base(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return _svc.platform.support_hub.knowledge_base(db)


@router.get("/support/claims")
def list_driver_claims(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return {"claims": _svc.platform.support_hub.list_claims(db, ctx.driver.id)}


@router.post("/support/claims")
def open_driver_claim(
    body: DriverClaimOpenRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    try:
        claim = _svc.platform.support_hub.open_claim(
            db,
            ctx.driver,
            order_id=body.order_id,
            claim_type=body.claim_type,
            description=body.description,
        )
        db.commit()
        return claim
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/support/emergency-contact")
def get_emergency_contact(ctx: Annotated[DriverContext, Depends(get_driver_context)]):
    return _svc.platform.support_hub.emergency_contact(ctx.driver)


@router.put("/support/emergency-contact")
def update_emergency_contact(
    body: EmergencyContactUpdateRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    result = _svc.platform.support_hub.update_emergency_contact(
        db, ctx.driver, name=body.name, phone=body.phone, relationship=body.relationship
    )
    db.commit()
    return result


@router.post("/support")
def create_support(
    body: SupportTicketRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    try:
        ticket = _svc.platform.support.create_ticket(
            db,
            ctx.driver,
            subject=body.subject,
            description=body.description,
            order_id=body.order_id,
            priority=body.priority,
            category=body.category,
        )
        db.commit()
        return ticket
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/incidents")
def list_incidents(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return {"incidents": _svc.platform.incidents.list_incidents(db, ctx.driver.id)}


@router.post("/incidents")
def report_incident(
    body: IncidentRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    incident = _svc.platform.incidents.report_incident(
        db,
        ctx.driver,
        incident_type=body.incident_type,
        description=body.description,
        order_id=body.order_id,
        location=body.location,
    )
    db.commit()
    return incident


@router.post("/emergency")
def emergency(
    body: EmergencyRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    result = _svc.platform.emergency.trigger(db, ctx.driver, location=body.location, message=body.message)
    db.commit()
    return result


@router.post("/push/register")
def register_push(
    body: PushRegisterRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    result = _svc.platform.push.register_device(
        db,
        ctx.driver,
        device_token=body.device_token,
        platform=body.platform,
    )
    db.commit()
    return result


@router.get("/communications")
def communications_hub(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    return _svc.platform.communications.snapshot(db, ctx.driver)


@router.get("/communications/notifications")
def communications_notifications(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    return _svc.platform.communications.inbox(db, ctx.driver.id)


@router.post("/communications/notifications/{notification_id}/read")
def communications_mark_read(
    notification_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    if not _svc.platform.communications.mark_read(db, ctx.driver.id, notification_id):
        raise HTTPException(status_code=404, detail="notification_not_found")
    db.commit()
    return {"ok": True}


@router.post("/communications/notifications/{notification_id}/archive")
def communications_mark_archive(
    notification_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    if not _svc.platform.communications.mark_archive(db, ctx.driver.id, notification_id):
        raise HTTPException(status_code=404, detail="notification_not_found")
    db.commit()
    return {"ok": True}


@router.post("/communications/notifications/mark-all-read")
def communications_mark_all_read(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    count = _svc.platform.communications.mark_all_read(db, ctx.driver.id)
    db.commit()
    return {"ok": True, "marked": count}


@router.get("/communications/notifications/history")
def communications_notifications_history(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    limit: int = Query(100, le=500),
):
    return _svc.platform.communications.inbox(db, ctx.driver.id, limit=limit, archived=True)


@router.get("/communications/offline")
def communications_offline(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    return _svc.platform.offline.status(db, ctx.driver.id)


@router.post("/communications/offline/retry")
def communications_offline_retry(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    result = _svc.persist(
        db,
        lambda: _svc.platform.offline.retry_failed(
            db, ctx.driver, executor=_svc.offline_executor(db, settings)
        ),
    )
    return result


@router.post("/location")
def location_ping(
    body: LocationPingRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = _svc.fleetbase_bridge(settings)
    result = _svc.platform.location.record_ping(
        db,
        ctx.driver,
        lat=body.lat,
        lng=body.lng,
        accuracy_m=body.accuracy_m,
        heading=body.heading,
        speed_mps=body.speed_mps,
        fleetbase_bridge=bridge,
    )
    db.commit()
    return result


@router.get("/jobs", response_model=DriverJobsListResponse)
def list_jobs(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    _guard_portal_ready(ctx, settings)
    return _svc.platform.jobs.list_jobs(db, ctx.driver)


@router.post("/jobs/optimize", response_model=DriverJobsOptimizeResponse)
def optimize_jobs(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    _guard_portal_ready(ctx, settings)
    require_approved_driver(ctx)
    try:
        result = _svc.platform.jobs.optimize_route(db, ctx.driver)
        db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/jobs/history")
def jobs_history(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    _guard_portal_ready(ctx, settings)
    return {"history": _svc.platform.jobs.order_history(db, ctx.driver)}


@router.get("/jobs/{order_id}", response_model=DriverJobDetailResponse)
def job_detail(
    order_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    _guard_portal_ready(ctx, settings)
    try:
        return _svc.platform.jobs.job_detail(db, ctx.driver, order_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="job_not_found") from exc


@router.get("/routes/assigned", response_model=RouteResponse | None)
def assignedroute_response(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    route = _svc.platform.stops.assignedroute_response(db, ctx.driver)
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
    bridge = _svc.fleetbase_bridge(settings)
    route = _svc.platform.stops.startroute_response(db, ctx.driver, route_id, fleetbase_bridge=bridge)
    db.commit()
    return route_response(route)


@router.get("/routes/{route_id}/stops")
def route_stops(
    route_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    stops = _svc.platform.stops.stops_forroute_response(db, ctx.driver.id, route_id)
    bridge = _svc.fleetbase_bridge(settings)
    nav = _svc.platform.navigation.route_for_stops(db, ctx.driver, route_id, settings, fleetbase_bridge=bridge)
    return {"stops": [stop_response(s) for s in stops], "route_polyline": nav.get("route_polyline")}


@router.get("/routes/{route_id}/earnings")
def route_earnings(
    route_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    return {"earnings_cents": _svc.platform.earnings.route_earnings_cents(db, ctx.driver.id, route_id)}


@router.post("/routes/{route_id}/stops/{stop_id}/arrive")
def arrivestop_response(
    route_id: str,
    stop_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = _svc.fleetbase_bridge(settings)
    try:
        stop = _svc.platform.stops.arrivestop_response(db, ctx.driver, stop_id, fleetbase_bridge=bridge)
        db.commit()
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
    bridge = _svc.fleetbase_bridge(settings)
    try:
        stop = _svc.platform.stops.deliverstop_response(
            db,
            ctx.driver,
            stop_id,
            fleetbase_bridge=bridge,
            auto_reoptimize=settings.enable_driver_auto_reoptimize,
        )
        db.commit()
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
    bridge = _svc.fleetbase_bridge(settings)
    result = _svc.platform.stops.report_exception(
        db,
        ctx.driver,
        stop_id,
        exception_type=body.exception_type,
        notes=body.notes,
        fleetbase_bridge=bridge,
    )
    db.commit()
    return result


@router.post("/orders/{order_id}/accept")
def accept_order(
    order_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = _svc.fleetbase_bridge(settings)
    try:
        result = _svc.platform.availability.accept_assignment(
            db, ctx.driver, order_id, fleetbase_bridge=bridge
        )
        db.commit()
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
    bridge = _svc.fleetbase_bridge(settings)
    try:
        result = _svc.platform.availability.reject_assignment(
            db, ctx.driver, order_id, reason=body.reason or "", fleetbase_bridge=bridge
        )
        db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="order_not_found") from exc


@router.get("/navigation/session")
def navigation_session(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    order_id: str | None = None,
):
    """Full navigation session — Fleetbase GPS, OSRM ETA, Valhalla route."""
    bridge = _svc.fleetbase_bridge(settings)
    if not order_id:
        jobs = _svc.platform.jobs.list_jobs(db, ctx.driver)
        current = jobs.get("current")
        if not current:
            return _svc.platform.navigation.idle_session(ctx.driver)
        order_id = current["order_id"]
    try:
        return _svc.platform.navigation.session(
            db, ctx.driver, order_id, settings, fleetbase_bridge=bridge
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="job_not_found") from exc


@router.get("/navigation/route")
def navigationroute_response(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    route_id: str | None = None,
):
    bridge = _svc.fleetbase_bridge(settings)
    if not route_id:
        route = _svc.platform.stops.assignedroute_response(db, ctx.driver)
        if not route:
            raise HTTPException(status_code=404, detail="route_not_found")
        route_id = route.route_id
    return _svc.platform.navigation.route_session(
        db, ctx.driver, route_id, settings, fleetbase_bridge=bridge
    )


@router.get("/orders/{order_id}/navigation")
def order_navigation(
    order_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    bridge = _svc.fleetbase_bridge(settings)
    try:
        return _svc.platform.navigation.route_for_order(
            db, ctx.driver, order_id, settings, fleetbase_bridge=bridge
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
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = _svc.fleetbase_bridge(settings)
    try:
        result = _svc.platform.pod.capture_photo(db, ctx.driver, stop_id, file_url=body.file_url, fleetbase_bridge=bridge)
        db.commit()
        return {"success": result.success, "fleetbase_synced": result.fleetbase_synced}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="stop_not_found") from exc


@router.post("/routes/{route_id}/stops/{stop_id}/pod-signature")
def pod_signature(
    route_id: str,
    stop_id: str,
    body: PodSignatureRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = _svc.fleetbase_bridge(settings)
    try:
        result = _svc.platform.pod.capture_signature(
            db, ctx.driver, stop_id, signature_data=body.signature_data, fleetbase_bridge=bridge
        )
        db.commit()
        return {"success": result.success, "fleetbase_synced": result.fleetbase_synced}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="stop_not_found") from exc


@router.post("/routes/{route_id}/stops/{stop_id}/pod-barcode")
def pod_barcode(
    route_id: str,
    stop_id: str,
    body: PodBarcodeRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = _svc.fleetbase_bridge(settings)
    try:
        result = _svc.platform.pod.capture_barcode(db, ctx.driver, stop_id, barcode=body.barcode, fleetbase_bridge=bridge)
        db.commit()
        return {"success": result.success, "fleetbase_synced": result.fleetbase_synced}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="stop_not_found") from exc


@router.post("/routes/{route_id}/stops/{stop_id}/pod-complete")
def pod_complete(
    route_id: str,
    stop_id: str,
    body: PodOtpRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = _svc.fleetbase_bridge(settings)
    try:
        result = _svc.platform.pod.complete_pod(db, ctx.driver, stop_id, otp=body.otp, fleetbase_bridge=bridge)
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        db.commit()
        return {"success": True, "state": "POD_COMPLETED"}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="stop_not_found") from exc


@router.post("/orders/{order_id}/otp")
def generate_otp(
    order_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    require_approved_driver(ctx)
    try:
        otp = _svc.platform.pod.generate_otp(db, ctx.driver, order_id)
        db.commit()
        return {"otp": otp}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="order_not_found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="order_not_assigned_to_driver") from exc


@router.post("/offline/queue")
def queue_offline(
    body: OfflineActionRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    result = _svc.platform.offline.queue_action(
        db,
        ctx.driver,
        action_type=body.action_type,
        payload=body.payload,
        client_id=body.client_id,
    )
    db.commit()
    return result


@router.get("/offline/pending")
def offline_pending(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return {"actions": _svc.platform.offline.list_pending(db, ctx.driver.id)}


@router.post("/offline/sync")
def offline_sync(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Replay queued offline actions through DriverPlatform (connectivity restored)."""
    require_approved_driver(ctx)
    return _svc.persist(
        db,
        lambda: _svc.platform.offline.sync_pending(
            db, ctx.driver, executor=_svc.offline_executor(db, settings)
        ),
    )


# Legacy companion routes per CONNECTIONS.md
legacy_router = APIRouter(prefix="/driver", tags=["driver-legacy"])


@legacy_router.post("/location")
def legacy_location(
    body: LocationPingRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = _svc.fleetbase_bridge(settings)
    result = _svc.platform.location.record_ping(
        db,
        ctx.driver,
        lat=body.lat,
        lng=body.lng,
        accuracy_m=body.accuracy_m,
        heading=body.heading,
        speed_mps=body.speed_mps,
        fleetbase_bridge=bridge,
    )
    db.commit()
    return result
