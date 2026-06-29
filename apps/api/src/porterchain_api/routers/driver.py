"""Driver platform API — /driver-api/v1/* extends Fleetbase capabilities."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from porterchain_api.auth.driver import get_driver_context
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.admin_models import Driver
from porterchain_api.driver_engine.fleetbase_bridge import DriverFleetbaseBridge
from porterchain_api.driver_engine.rbac import DriverContext, require_approved_driver
from porterchain_api.schemas_driver import (
    AcceptRejectRequest,
    AvailabilityRequest,
    DocumentUploadRequest,
    DriverDashboardResponse,
    DriverLoginRequest,
    DriverProfileResponse,
    DriverTokenResponse,
    EmergencyRequest,
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
    StopResponse,
    SupportTicketRequest,
)
from porterchain_driver import DriverPlatform
from porterchain_driver.auth_tokens import issue_driver_session

router = APIRouter(prefix="/driver-api/v1", tags=["driver"])
_platform = DriverPlatform()


def _profile(driver: Driver) -> DriverProfileResponse:
    return DriverProfileResponse(
        id=driver.id,
        full_name=driver.full_name,
        email=driver.email,
        phone=driver.phone,
        status=driver.status,
        rating=driver.rating,
        is_online=bool(driver.is_online),
        availability=driver.availability or "offline",
        wallet_balance_cents=driver.wallet_balance_cents or 0,
        license_verified=driver.license_verified,
        insurance_verified=driver.insurance_verified,
        vehicle_verified=driver.vehicle_verified,
        fleetbase_driver_id=driver.fleetbase_driver_id,
    )


def _stop(s) -> StopResponse:
    return StopResponse(
        stop_id=s.stop_id,
        order_id=s.order_id,
        sequence=s.sequence,
        stop_type=s.stop_type,
        status=s.status,
        address=s.address,
        scheduled_at=s.scheduled_at,
        tracking_number=s.tracking_number,
        order_number=s.order_number,
        special_instructions=s.special_instructions,
        otp_required=s.otp_required,
        pod_required=s.pod_required,
    )


def _route(r) -> RouteResponse:
    return RouteResponse(
        route_id=r.route_id,
        driver_id=r.driver_id,
        status=r.status,
        stops=[_stop(s) for s in r.stops],
        route_polyline=r.route_polyline,
        earnings_cents=r.earnings_cents,
        started_at=r.started_at,
    )


@router.post("/auth/login", response_model=DriverTokenResponse)
def driver_login(body: DriverLoginRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    """Driver JWT login — Porterchain-issued tokens for mobile execution."""
    driver = db.query(Driver).filter(Driver.email == body.email).first()
    if not driver:
        raise HTTPException(status_code=404, detail="driver_not_found")
    if driver.status not in (DriverStatus.APPROVED.value, DriverStatus.PENDING.value):
        raise HTTPException(status_code=403, detail="driver_not_active")
    tokens = issue_driver_session(driver.id, secret=settings.jwt_secret, email=driver.email)
    return DriverTokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in_seconds,
        driver_id=driver.id,
    )


@router.get("/me", response_model=DriverProfileResponse)
def driver_me(ctx: Annotated[DriverContext, Depends(get_driver_context)]):
    return _profile(ctx.driver)


@router.get("/dashboard", response_model=DriverDashboardResponse)
def dashboard(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    snap = _platform.dashboard.snapshot(db, ctx.driver)
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


@router.get("/earnings/today")
def earnings_today(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return {
        "today_cents": _platform.earnings.today_cents(db, ctx.driver.id),
        "week_cents": _platform.earnings.week_cents(db, ctx.driver.id),
    }


@router.get("/wallet")
def wallet(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return {
        "balance_cents": _platform.wallet.balance_cents(ctx.driver),
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
            for t in _platform.wallet.list_transactions(db, ctx.driver.id)
        ],
        "payouts": _platform.wallet.list_payouts(db, ctx.driver.id),
    }


@router.get("/bonuses")
def bonuses(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return {"bonuses": _platform.bonuses.list_bonuses(db, ctx.driver.id)}


@router.post("/bonuses/{bonus_id}/claim")
def claim_bonus(
    bonus_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    try:
        result = _platform.bonuses.claim_bonus(db, ctx.driver, bonus_id)
        db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="bonus_not_found") from exc


@router.get("/performance")
def performance(ctx: Annotated[DriverContext, Depends(get_driver_context)]):
    return _platform.performance.summary(ctx.driver)


@router.get("/ratings")
def ratings(ctx: Annotated[DriverContext, Depends(get_driver_context)]):
    return _platform.ratings.summary(ctx.driver)


@router.post("/availability")
def set_availability(
    body: AvailabilityRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = DriverFleetbaseBridge(settings)
    try:
        result = _platform.availability.set_online(db, ctx.driver, online=body.online, fleetbase_bridge=bridge)
        db.commit()
        return result
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/vehicle")
def get_vehicle(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return {"vehicle": _platform.vehicle.get_active_vehicle(db, ctx.driver.id), "vehicles": _platform.vehicle.list_vehicles(db, ctx.driver.id)}


@router.get("/insurance")
def insurance(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return _platform.insurance.status(db, ctx.driver)


@router.get("/documents")
def list_documents(ctx: Annotated[DriverContext, Depends(get_driver_context)]):
    return {"documents": _platform.documents.list_documents(ctx.driver)}


@router.post("/documents")
def upload_document(
    body: DocumentUploadRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    doc = _platform.documents.upload_document(
        db, ctx.driver, doc_type=body.doc_type, file_url=body.file_url, metadata=body.metadata
    )
    db.commit()
    return doc


@router.get("/training")
def training(ctx: Annotated[DriverContext, Depends(get_driver_context)]):
    return {"modules": _platform.training.list_modules(ctx.driver)}


@router.post("/training/{module_id}/complete")
def complete_training(
    module_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    result = _platform.training.complete_module(db, ctx.driver, module_id)
    db.commit()
    return result


@router.get("/support")
def list_support(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return {"tickets": _platform.support.list_tickets(db, ctx.driver.id)}


@router.post("/support")
def create_support(
    body: SupportTicketRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    ticket = _platform.support.create_ticket(
        db, ctx.driver, subject=body.subject, description=body.description, order_id=body.order_id, priority=body.priority
    )
    db.commit()
    return ticket


@router.get("/incidents")
def list_incidents(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return {"incidents": _platform.incidents.list_incidents(db, ctx.driver.id)}


@router.post("/incidents")
def report_incident(
    body: IncidentRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    incident = _platform.incidents.report_incident(
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
    result = _platform.emergency.trigger(db, ctx.driver, location=body.location, message=body.message)
    db.commit()
    return result


@router.post("/push/register")
def register_push(
    body: PushRegisterRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    result = _platform.push.register_device(db, ctx.driver, device_token=body.device_token, platform=body.platform)
    db.commit()
    return result


@router.post("/location")
def location_ping(
    body: LocationPingRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = DriverFleetbaseBridge(settings)
    result = _platform.location.record_ping(
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


@router.get("/routes/assigned", response_model=RouteResponse | None)
def assigned_route(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    route = _platform.stops.assigned_route(db, ctx.driver)
    if not route:
        return None
    bridge = DriverFleetbaseBridge(settings)
    nav = _platform.navigation.route_for_stops(db, ctx.driver, route.route_id, fleetbase_bridge=bridge)
    route.route_polyline = nav.get("route_polyline")
    return _route(route)


@router.post("/routes/{route_id}/start", response_model=RouteResponse)
def start_route(
    route_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    require_approved_driver(ctx)
    route = _platform.stops.start_route(db, ctx.driver, route_id)
    db.commit()
    return _route(route)


@router.get("/routes/{route_id}/stops")
def route_stops(
    route_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    stops = _platform.stops.stops_for_route(db, ctx.driver.id, route_id)
    bridge = DriverFleetbaseBridge(settings)
    nav = _platform.navigation.route_for_stops(db, ctx.driver, route_id, fleetbase_bridge=bridge)
    return {"stops": [_stop(s) for s in stops], "route_polyline": nav.get("route_polyline")}


@router.get("/routes/{route_id}/earnings")
def route_earnings(
    route_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    return {"earnings_cents": _platform.earnings.route_earnings_cents(db, ctx.driver.id, route_id)}


@router.post("/routes/{route_id}/stops/{stop_id}/arrive")
def arrive_stop(
    route_id: str,
    stop_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = DriverFleetbaseBridge(settings)
    stop = _platform.stops.arrive_stop(db, ctx.driver, stop_id, fleetbase_bridge=bridge)
    db.commit()
    return _stop(stop)


@router.post("/routes/{route_id}/stops/{stop_id}/deliver")
def deliver_stop(
    route_id: str,
    stop_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = DriverFleetbaseBridge(settings)
    stop = _platform.stops.deliver_stop(db, ctx.driver, stop_id, fleetbase_bridge=bridge)
    db.commit()
    return _stop(stop)


@router.post("/routes/{route_id}/stops/{stop_id}/exception")
def stop_exception(
    route_id: str,
    stop_id: str,
    body: ExceptionRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    result = _platform.stops.report_exception(
        db, ctx.driver, stop_id, exception_type=body.exception_type, notes=body.notes
    )
    db.commit()
    return result


@router.post("/orders/{order_id}/accept")
def accept_order(
    order_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    require_approved_driver(ctx)
    try:
        result = _platform.availability.accept_assignment(db, ctx.driver, order_id)
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
):
    try:
        result = _platform.availability.reject_assignment(db, ctx.driver, order_id, reason=body.reason or "")
        db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="order_not_found") from exc


@router.get("/orders/{order_id}/navigation")
def order_navigation(
    order_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    bridge = DriverFleetbaseBridge(settings)
    try:
        return _platform.navigation.route_for_order(db, ctx.driver, order_id, fleetbase_bridge=bridge)
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
    bridge = DriverFleetbaseBridge(settings)
    try:
        result = _platform.pod.capture_photo(db, ctx.driver, stop_id, file_url=body.file_url, fleetbase_bridge=bridge)
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
    bridge = DriverFleetbaseBridge(settings)
    try:
        result = _platform.pod.capture_signature(
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
    bridge = DriverFleetbaseBridge(settings)
    try:
        result = _platform.pod.capture_barcode(db, ctx.driver, stop_id, barcode=body.barcode, fleetbase_bridge=bridge)
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
    bridge = DriverFleetbaseBridge(settings)
    try:
        result = _platform.pod.complete_pod(db, ctx.driver, stop_id, otp=body.otp, fleetbase_bridge=bridge)
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
    try:
        otp = _platform.pod.generate_otp(db, order_id)
        db.commit()
        return {"otp": otp}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="order_not_found") from exc


@router.post("/offline/queue")
def queue_offline(
    body: OfflineActionRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    result = _platform.offline.queue_action(db, ctx.driver, action_type=body.action_type, payload=body.payload)
    db.commit()
    return result


@router.get("/offline/pending")
def offline_pending(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return {"actions": _platform.offline.list_pending(db, ctx.driver.id)}


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
    bridge = DriverFleetbaseBridge(settings)
    result = _platform.location.record_ping(
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
