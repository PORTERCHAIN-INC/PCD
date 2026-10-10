"""Driver 360 admin API — /v1/admin/drivers/*

Driver approval, verification, wallet, payouts, documents, support and
compliance are Porterchain business logic (masterrule.md). Reads the Porterchain
PorterChain orders.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.crm_sales_service import CrmSalesService
from porterchain_api.admin_engine.driver360_service import Driver360Service
from porterchain_api.admin_engine.driver_service import AdminDriverService
from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.auth.driver_admin_action import run_admin_driver_action
from porterchain_api.auth.invitation_service import InvitationService
from porterchain_api.billing_engine.driver_finance_service import DriverFinanceService
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.platform.pagination import (
    DEFAULT_LIST_LIMIT,
    DEFAULT_PAGE_SIZE,
    MAX_EMBEDDED_LIST_LIMIT,
    MAX_LIST_LIMIT,
)
from porterchain_api.schemas_admin import (
    DriverActionRequest,
    DriverCreateRequest,
    DriverDocumentInput,
    DriverPayoutCreateRequest,
    DriverRejectRequest,
    DriverVerifyRequest,
)
from porterchain_api.schemas_crm import ActivityOut, TaskOut

router = APIRouter(prefix="/v1/admin/drivers", tags=["drivers"])

_d360 = Driver360Service()
_drivers = AdminDriverService()
_crm = CrmSalesService()
_invites = InvitationService()
_finance = DriverFinanceService()
Ctx = Annotated[AdminContext, Depends(get_admin_context)]


def _invoke(ctx: AdminContext, module: str, fn, *args, **kwargs):
    try:
        require_module(ctx, module)
        return fn(*args, **kwargs)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc) or "driver_not_found") from exc
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except RuntimeError as exc:
        if str(exc) == "clerk_not_configured":
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        raise
    except ValueError as exc:
        if str(exc) == "driver_email_exists":
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _detail(db: Session, driver_id: str) -> dict:
    detail = _d360.detail(db, driver_id)
    if not detail:
        raise HTTPException(status_code=404, detail="driver_not_found")
    return detail


def _mutated(ctx: AdminContext, db: Session, driver_id: str, fn, *args, **kwargs) -> dict:
    _invoke(ctx, "drivers", fn, db, ctx, driver_id, *args, **kwargs)
    return _detail(db, driver_id)


def _vehicle(vehicle) -> dict:
    return {
        "id": vehicle.id,
        "vehicle_class": getattr(vehicle, "vehicle_class", None),
        "plate_number": getattr(vehicle, "plate_number", None),
        "is_active": vehicle.is_active,
    }


@router.get("")
def list_drivers(
    ctx: Ctx,
    db: Session = Depends(get_db),
    status: str | None = None,
    background_check: str | None = None,
    search: str | None = None,
    limit: int = Query(DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT),
) -> list[dict]:
    return _invoke(
        ctx, "drivers_read", _d360.list_drivers, db,
        status=status, background_check=background_check, search=search, limit=limit,
    )


@router.get("/facets")
def driver_facets(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "drivers_read", _d360.facets, db)


@router.get("/stats")
def driver_stats(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "drivers_read", _d360.stats, db)


@router.post("", status_code=201)
def create_driver(
    body: DriverCreateRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Provision a driver from admin — identity, vehicle, and compliance documents."""
    driver = _invoke(ctx, "drivers", _drivers.create_driver, db, ctx, body, settings)
    return _detail(db, driver.id)


@router.get("/{driver_id}")
def driver_detail(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "drivers_read", _detail, db, driver_id)


@router.post("/{driver_id}/invite")
def invite_driver(
    driver_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Resend Clerk invitation for an existing driver."""
    driver = _invoke(ctx, "drivers", _drivers.get_driver, db, driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="driver_not_found")
    return _invoke(ctx, "drivers", _invites.invite_existing_driver, db, ctx, settings, driver)


@router.post("/{driver_id}/approve")
def approve_driver(
    driver_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    return _mutated(ctx, db, driver_id, _drivers.approve_driver, settings)


@router.post("/{driver_id}/suspend")
def suspend_driver(
    driver_id: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> dict:
    return _mutated(ctx, db, driver_id, _drivers.suspend_driver, settings)


@router.post("/{driver_id}/deactivate")
def deactivate_driver(
    driver_id: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> dict:
    """Explicit deactivate — same lifecycle as suspend (D-30)."""
    return _mutated(ctx, db, driver_id, _drivers.deactivate_driver, settings)


@router.post("/{driver_id}/reject")
def reject_driver(
    driver_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    body: DriverRejectRequest | None = None,
) -> dict:
    return _mutated(
        ctx,
        db,
        driver_id,
        _drivers.reject_driver,
        settings,
        reason=body.reason if body else None,
    )


@router.post("/{driver_id}/rehire")
def rehire_driver(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _mutated(ctx, db, driver_id, _drivers.rehire_driver)


@router.patch("/{driver_id}/verification")
def verify_driver(driver_id: str, body: DriverVerifyRequest, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _mutated(ctx, db, driver_id, _drivers.update_verification, **body.model_dump(exclude_unset=True))


@router.post("/{driver_id}/action")
def driver_action(driver_id: str, body: DriverActionRequest, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Operational driver action — push/SMS/email via Notification Engine."""
    driver = _invoke(ctx, "drivers", _drivers.get_driver, db, driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="driver_not_found")
    return _invoke(
        ctx,
        "drivers",
        run_admin_driver_action,
        db,
        driver,
        body.type,
        body.message,
        ctx.user.id if ctx.user else None,
    )


@router.get("/{driver_id}/orders")
def driver_orders(
    driver_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
    state: str | None = None,
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_EMBEDDED_LIST_LIMIT),
    offset: int = Query(0, ge=0),
) -> dict:
    return _invoke(ctx, "drivers_read", _d360.orders, db, driver_id, state=state, limit=limit, offset=offset)


@router.get("/{driver_id}/vehicles")
def driver_vehicles(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    return _invoke(ctx, "drivers_read", _d360.vehicles, db, driver_id)


@router.get("/{driver_id}/payouts")
def driver_payouts(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "drivers_read", _d360.payouts, db, driver_id)


@router.post("/{driver_id}/payouts", status_code=201)
def create_driver_payout(
    driver_id: str,
    body: DriverPayoutCreateRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
) -> dict:
    """Create a pending payout from wallet balance (D-24)."""
    return _finance.payout_payload(
        _invoke(
            ctx,
            "drivers",
            _finance.create_payout,
            db,
            driver_id,
            amount_cents=body.amount_cents,
            reference=body.reference,
        )
    )


@router.post("/{driver_id}/payouts/{payout_id}/mark-paid")
def mark_driver_payout_paid(
    driver_id: str,
    payout_id: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
) -> dict:
    return _finance.payout_payload(
        _invoke(ctx, "drivers", _finance.mark_payout_paid, db, payout_id, driver_id=driver_id)
    )


@router.get("/{driver_id}/documents")
def driver_documents(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "drivers_read", _d360.documents, db, driver_id)


@router.post("/{driver_id}/documents", status_code=201)
def add_driver_document(
    driver_id: str,
    body: DriverDocumentInput,
    ctx: Ctx,
    db: Session = Depends(get_db),
) -> dict:
    """Attach a compliance document record (URL or reference) to a driver profile."""
    _invoke(ctx, "drivers", _drivers.add_document, db, ctx, driver_id, body)
    return _d360.documents(db, driver_id)


@router.get("/{driver_id}/incidents")
def driver_incidents(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "drivers_read", _d360.incidents, db, driver_id)


@router.get("/{driver_id}/analytics")
def driver_analytics(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "drivers_read", _d360.analytics, db, driver_id)


@router.get("/{driver_id}/timeline")
def driver_timeline(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    return _invoke(ctx, "drivers_read", _d360.timeline, db, driver_id)


@router.get("/{driver_id}/activities", response_model=list[ActivityOut])
def driver_activities(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[ActivityOut]:
    rows = _invoke(ctx, "drivers_read", _crm.list_activities, db, entity_type="driver", entity_id=driver_id)
    return [ActivityOut(**_crm.activity_dict(a)) for a in rows]


@router.get("/{driver_id}/tasks", response_model=list[TaskOut])
def driver_tasks(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> list[TaskOut]:
    rows = _invoke(ctx, "drivers_read", _crm.list_tasks, db, entity_id=driver_id)
    return [TaskOut.model_validate(t) for t in rows]
