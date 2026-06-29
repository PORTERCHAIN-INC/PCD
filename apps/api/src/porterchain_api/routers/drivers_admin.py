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
from porterchain_api.db import get_db
from porterchain_api.schemas_admin import DriverVerifyRequest
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
    availability: str | None = None,
    background_check: str | None = None,
    search: str | None = None,
    limit: int = Query(1000, le=10000),
) -> list[dict]:
    _guard(ctx, "drivers_read")
    return _d360.list_drivers(
        db, status=status, availability=availability, background_check=background_check, search=search, limit=limit
    )


@router.get("/facets")
def driver_facets(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "drivers_read")
    return _d360.facets(db)


@router.get("/stats")
def driver_stats(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "drivers_read")
    return _d360.stats(db)


# --------------------------------------------------------------------------- #
# Detail + lifecycle
# --------------------------------------------------------------------------- #
@router.get("/{driver_id}")
def driver_detail(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "drivers_read")
    return _detail_or_404(db, driver_id)


@router.post("/{driver_id}/approve")
def approve_driver(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "drivers")
    try:
        _drivers.approve_driver(db, ctx, driver_id, None)
    except LookupError:
        raise HTTPException(status_code=404, detail="driver_not_found") from None
    return _detail_or_404(db, driver_id)


@router.post("/{driver_id}/suspend")
def suspend_driver(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "drivers")
    try:
        _drivers.suspend_driver(db, ctx, driver_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="driver_not_found") from None
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


_ACTION_LABEL = {
    "push": "Push notification sent",
    "sms": "SMS sent",
    "email": "Email sent",
    "request_documents": "Documents requested",
    "reset_password": "Password reset link sent",
}


@router.post("/{driver_id}/action")
def driver_action(driver_id: str, body: DriverActionRequest, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Operational driver action — recorded as an auditable activity.

    Delivery (push/SMS/email) is dispatched by the Porterchain notification
    service; this records intent + audit on the driver timeline.
    """
    _guard(ctx, "drivers")
    if not _drivers.get_driver(db, driver_id):
        raise HTTPException(status_code=404, detail="driver_not_found")
    subject = _ACTION_LABEL.get(body.type, body.type)
    _crm.log_activity(
        db,
        entity_type="driver",
        entity_id=driver_id,
        activity_type="email" if body.type == "email" else "system",
        subject=subject,
        body=body.message,
        actor_id=ctx.user.id if ctx.user else None,
    )
    return {"ok": True, "action": body.type}


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


@router.get("/{driver_id}/payouts")
def driver_payouts(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "drivers_read")
    return _d360.payouts(db, driver_id)


@router.get("/{driver_id}/documents")
def driver_documents(driver_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "drivers_read")
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
