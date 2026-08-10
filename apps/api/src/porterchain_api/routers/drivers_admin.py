"""Driver 360 admin API — /v1/admin/drivers/*

Driver approval, verification, wallet, payouts, documents, support and
compliance are Porterchain business logic (masterrule.md). Reads the Porterchain
order mirror; Fleetbase sync stays inside the driver service / adapter layer.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.crm_sales_service import CrmSalesService
from porterchain_api.admin_engine.driver360_service import Driver360Service
from porterchain_api.admin_engine.driver_service import AdminDriverService
from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.auth.clerk_registry import is_clerk_secret_configured
from porterchain_api.db import get_db, db_transaction
from porterchain_api.platform.pagination import DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT
from porterchain_api.config import Settings, get_settings
from porterchain_api.schemas_admin import (
    DriverCreateRequest,
    DriverDocumentInput,
    DriverVehicleCreateInput,
    DriverVerifyRequest,
)
from porterchain_api.schemas_crm import ActivityOut, TaskOut

router = APIRouter(prefix="/v1/admin/drivers", tags=["drivers"])

_d360 = Driver360Service()
_drivers = AdminDriverService()
_crm = CrmSalesService()

Ctx = Annotated[AdminContext, Depends(get_admin_context)]


def _guard(ctx: AdminContext, module: str) -> None:
    try:
        require_module(ctx, module)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _detail_or_404(db: Session, driver_id: str) -> dict:
    detail = _d360.detail(db, driver_id)
    if not detail:
        raise HTTPException(status_code=404, detail="driver_not_found")
    return detail


# --------------------------------------------------------------------------- #
# List / facets / stats
# --------------------------------------------------------------------------- #
@router.get("")
def list_drivers(
    ctx: Ctx,
    db: Session = Depends(get_db),
    status: str | None = None,
    background_check: str | None = None,
    search: str | None = None,
    limit: int = Query(DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT),
) -> list[dict]:
    _guard(ctx, "drivers_read")
    return _d360.list_drivers(
        db, status=status, background_check=background_check, search=search, limit=limit
    )


@router.get("/facets")
def driver_facets(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "drivers_read")
    return _d360.facets(db)


@router.get("/stats")
def driver_stats(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "drivers_read")
    return _d360.stats(db)


@router.post("", status_code=201)
def create_driver(
    body: DriverCreateRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Provision a driver from admin — identity, vehicle, and compliance documents."""
    _guard(ctx, "drivers")
    try:
        driver = _drivers.create_driver(
            db,
            ctx,
            body,
            settings,
        )
    except ValueError as exc:
        if str(exc) == "driver_email_exists":
            raise HTTPException(status_code=409, detail="driver_email_exists") from exc
        raise
    return _detail_or_404(db, driver.id)


# --------------------------------------------------------------------------- #
# Detail + lifecycle
# --------------------------------------------------------------------------- #
@router.get("/{driver_id}")
def driver_detail(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "drivers_read")
    return _detail_or_404(db, driver_id)


@router.post("/{driver_id}/invite")
def invite_driver(
    driver_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Resend Clerk invitation for an existing driver."""
    _guard(ctx, "drivers")
    driver = _drivers.get_driver(db, driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="driver_not_found")
    if not is_clerk_secret_configured(settings, "driver"):
        raise HTTPException(status_code=503, detail="clerk_not_configured")
    from porterchain_api.auth.invitation_service import InvitationService

    invitation = InvitationService().invite_driver(db, ctx, settings, driver)
    return {
        "driver_id": driver.id,
        "email": driver.email,
        "invitation_status": invitation.status,
        "clerk_action": invitation.invitation_metadata.get("clerk_action"),
    }


@router.post("/{driver_id}/approve")
def approve_driver(
    driver_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    _guard(ctx, "drivers")
    try:
        _drivers.approve_driver(db, ctx, driver_id, settings)
    except LookupError:
        raise HTTPException(status_code=404, detail="driver_not_found") from None
    return _detail_or_404(db, driver_id)


@router.post("/{driver_id}/suspend")
def suspend_driver(driver_id: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> dict:
    _guard(ctx, "drivers")
    try:
        _driver, warning = _drivers.suspend_driver(db, ctx, driver_id, settings)
    except LookupError:
        raise HTTPException(status_code=404, detail="driver_not_found") from None
    detail = _detail_or_404(db, driver_id)
    if warning:
        detail["fleetbase_sync_warning"] = warning
    return detail


@router.post("/{driver_id}/deactivate")
def deactivate_driver(
    driver_id: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> dict:
    """Explicit deactivate — same lifecycle as suspend (D-30)."""
    _guard(ctx, "drivers")
    try:
        _driver, warning = _drivers.deactivate_driver(db, ctx, driver_id, settings)
    except LookupError:
        raise HTTPException(status_code=404, detail="driver_not_found") from None
    detail = _detail_or_404(db, driver_id)
    if warning:
        detail["fleetbase_sync_warning"] = warning
    return detail


@router.post("/{driver_id}/reject")
def reject_driver(
    driver_id: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> dict:
    _guard(ctx, "drivers")
    try:
        _driver, warning = _drivers.reject_driver(db, ctx, driver_id, settings)
    except LookupError:
        raise HTTPException(status_code=404, detail="driver_not_found") from None
    detail = _detail_or_404(db, driver_id)
    if warning:
        detail["fleetbase_sync_warning"] = warning
    return detail


@router.post("/{driver_id}/rehire")
def rehire_driver(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "drivers")
    try:
        _drivers.rehire_driver(db, ctx, driver_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="driver_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return _detail_or_404(db, driver_id)


@router.patch("/{driver_id}/verification")
def verify_driver(driver_id: str, body: DriverVerifyRequest, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "drivers")
    try:
        _drivers.update_verification(db, ctx, driver_id, **body.model_dump(exclude_unset=True))
    except LookupError:
        raise HTTPException(status_code=404, detail="driver_not_found") from None
    return _detail_or_404(db, driver_id)


class DriverActionRequest(BaseModel):
    type: str  # push | sms | email | request_documents | reset_password
    message: str | None = None


class DriverPayoutCreateRequest(BaseModel):
    amount_cents: int | None = None
    reference: str | None = None


_ACTION_LABEL = {
    "push": "Push notification sent",
    "sms": "SMS sent",
    "email": "Email sent",
}


@router.post("/{driver_id}/action")
def driver_action(driver_id: str, body: DriverActionRequest, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Operational driver action — push/SMS/email via Notification Engine."""
    _guard(ctx, "drivers")
    driver = _drivers.get_driver(db, driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="driver_not_found")

    if body.type in ("request_documents", "reset_password"):
        # D-5: do not fake success — Clerk password reset / doc request not wired yet.
        raise HTTPException(status_code=501, detail=f"{body.type}_not_implemented")

    delivery_status = "queued"
    delivery_detail: str | None = None

    if body.type == "push":
        from porterchain_api.notification_engine.fcm_service import firebase_credentials_configured
        from porterchain_driver.platform import DriverPlatform
        from porterchain_shared.config.settings import get_platform_settings

        ps = get_platform_settings()
        if not getattr(ps, "push_enabled", True):
            delivery_status, delivery_detail = "logged", "push_disabled"
        elif not getattr(ps, "push_send", True) or not firebase_credentials_configured():
            delivery_status, delivery_detail = "logged", "push_log_only"
        DriverPlatform().push.notify_driver(
            db,
            driver,
            title="Message from Porterchain",
            body=body.message or "You have a new notification from operations.",
        )
    elif body.type == "email" and driver.email:
        from porterchain_api.notification_engine.engine import get_notification_engine

        get_notification_engine().dispatch(
            db,
            event_type="admin.driver_action",
            template_key="delivery_update",
            channel="email",
            recipient_type="driver",
            recipient_id=driver.id,
            recipient_address=driver.email,
            context={"message": body.message or "Message from Porterchain operations."},
        )
    elif body.type == "sms" and driver.phone:
        from porterchain_api.notification_engine.engine import get_notification_engine
        from porterchain_shared.config.settings import get_platform_settings

        ps = get_platform_settings()
        if not getattr(ps, "sms_enabled", False):
            delivery_status, delivery_detail = "logged", "sms_disabled"
        elif not (getattr(ps, "sms_provider", "") or "").strip():
            delivery_status, delivery_detail = "logged", "sms_provider_missing"
        get_notification_engine().dispatch(
            db,
            event_type="admin.driver_action",
            template_key="delivery_update",
            channel="sms",
            recipient_type="driver",
            recipient_id=driver.id,
            recipient_address=driver.phone,
            context={"message": body.message or "Message from Porterchain operations."},
        )
    elif body.type == "email" and not driver.email:
        raise HTTPException(status_code=400, detail="driver_email_missing")
    elif body.type == "sms" and not driver.phone:
        raise HTTPException(status_code=400, detail="driver_phone_missing")
    elif body.type not in ("push", "email", "sms"):
        raise HTTPException(status_code=400, detail="unsupported_driver_action")

    with db_transaction(db):
        subject = _ACTION_LABEL.get(body.type, body.type)
        if delivery_status == "logged":
            subject = f"{subject} (log-only — not delivered)"
        _crm.log_activity(
            db,
            entity_type="driver",
            entity_id=driver_id,
            activity_type="email" if body.type == "email" else "system",
            subject=subject,
            body=body.message,
            actor_id=ctx.user.id if ctx.user else None,
        )
    return {
        "ok": True,
        "action": body.type,
        "delivery_status": delivery_status,
        "detail": delivery_detail,
    }


# --------------------------------------------------------------------------- #
# 360 sub-resources
# --------------------------------------------------------------------------- #
@router.get("/{driver_id}/orders")
def driver_orders(driver_id: str, ctx: Ctx, db: Session = Depends(get_db), state: str | None = None) -> list[dict]:
    _guard(ctx, "drivers_read")
    return _d360.orders(db, driver_id, state=state)


@router.get("/{driver_id}/vehicles")
def driver_vehicles(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    _guard(ctx, "drivers_read")
    return _d360.vehicles(db, driver_id)


@router.post("/{driver_id}/vehicles", status_code=201)
def attach_driver_vehicle(
    driver_id: str,
    body: DriverVehicleCreateInput,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """D-29: attach vehicle and sync Fleetbase when bridge enabled."""
    _guard(ctx, "drivers")
    try:
        vehicle = _drivers.attach_vehicle(
            db,
            ctx,
            driver_id,
            vehicle_class=body.vehicle_class,
            plate_number=body.plate_number,
            make_model=body.make_model,
            capacity_kg=body.capacity_kg,
            settings=settings,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="driver_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": vehicle.id,
        "vehicle_class": vehicle.vehicle_class,
        "plate_number": vehicle.plate_number,
        "is_active": vehicle.is_active,
        "fleetbase_vehicle_id": vehicle.fleetbase_vehicle_id,
    }


@router.post("/{driver_id}/vehicles/{vehicle_id}/deactivate")
def deactivate_driver_vehicle(
    driver_id: str,
    vehicle_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """D-29: deactivate vehicle and push inactive state to Fleetbase."""
    _guard(ctx, "drivers")
    try:
        vehicle = _drivers.deactivate_vehicle(
            db, ctx, driver_id, vehicle_id, settings=settings
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "id": vehicle.id,
        "is_active": vehicle.is_active,
        "fleetbase_vehicle_id": vehicle.fleetbase_vehicle_id,
    }


@router.get("/{driver_id}/payouts")
def driver_payouts(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "drivers_read")
    return _d360.payouts(db, driver_id)


@router.post("/{driver_id}/payouts", status_code=201)
def create_driver_payout(
    driver_id: str,
    body: DriverPayoutCreateRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
) -> dict:
    """Create a pending payout from wallet balance (D-24)."""
    _guard(ctx, "drivers")
    from porterchain_api.billing_engine.driver_finance_service import DriverFinanceService

    try:
        payout = DriverFinanceService().create_payout(
            db,
            driver_id,
            amount_cents=body.amount_cents,
            reference=body.reference,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="driver_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return {
        "id": payout.id,
        "amount_cents": payout.amount_cents,
        "currency": payout.currency,
        "status": payout.status,
        "reference": payout.reference,
        "created_at": payout.created_at.isoformat() if payout.created_at else None,
    }


@router.post("/{driver_id}/payouts/{payout_id}/mark-paid")
def mark_driver_payout_paid(
    driver_id: str,
    payout_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
) -> dict:
    _guard(ctx, "drivers")
    from porterchain_api.admin_models import DriverPayout
    from porterchain_api.billing_engine.driver_finance_service import DriverFinanceService

    row = db.get(DriverPayout, payout_id)
    if not row or row.driver_id != driver_id:
        raise HTTPException(status_code=404, detail="payout_not_found")
    try:
        payout = DriverFinanceService().mark_payout_paid(db, payout_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="payout_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return {
        "id": payout.id,
        "amount_cents": payout.amount_cents,
        "currency": payout.currency,
        "status": payout.status,
        "reference": payout.reference,
        "created_at": payout.created_at.isoformat() if payout.created_at else None,
    }


@router.get("/{driver_id}/documents")
def driver_documents(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "drivers_read")
    try:
        return _d360.documents(db, driver_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="driver_not_found") from None


@router.post("/{driver_id}/documents", status_code=201)
def add_driver_document(
    driver_id: str,
    body: DriverDocumentInput,
    ctx: Ctx,
    db: Session = Depends(get_db),
) -> dict:
    """Attach a compliance document record (URL or reference) to a driver profile."""
    _guard(ctx, "drivers")
    try:
        _drivers.add_document(db, ctx, driver_id, body)
    except LookupError:
        raise HTTPException(status_code=404, detail="driver_not_found") from None
    return _d360.documents(db, driver_id)


@router.get("/{driver_id}/incidents")
def driver_incidents(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "drivers_read")
    return _d360.incidents(db, driver_id)


@router.get("/{driver_id}/analytics")
def driver_analytics(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "drivers_read")
    return _d360.analytics(db, driver_id)


@router.get("/{driver_id}/timeline")
def driver_timeline(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    _guard(ctx, "drivers_read")
    return _d360.timeline(db, driver_id)


@router.get("/{driver_id}/activities", response_model=list[ActivityOut])
def driver_activities(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[ActivityOut]:
    _guard(ctx, "drivers_read")
    rows = _crm.list_activities(db, entity_type="driver", entity_id=driver_id)
    return [ActivityOut(**_crm.activity_dict(a)) for a in rows]


@router.get("/{driver_id}/tasks", response_model=list[TaskOut])
def driver_tasks(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[TaskOut]:
    _guard(ctx, "drivers_read")
    rows = _crm.list_tasks(db, entity_id=driver_id)
    return [TaskOut.model_validate(t) for t in rows]
