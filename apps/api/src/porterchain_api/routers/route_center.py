"""Enterprise Route Center API — /v1/admin/route-center/*

Planning, optimization, dispatch orchestration. Fleetbase execution only via adapter.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.route_center_service import RouteCenterService
from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.schemas_route_center import (
    RouteBulkDispatchRequest,
    RouteCenterDashboard,
    RouteDispatchRequest,
    RouteOptimizeRequest,
    RoutePlanCreate,
    RoutePlanMerge,
    RoutePlanSplit,
    RoutePlanUpdate,
    RouteTemplateCreatePlan,
    RouteTemplateSave,
)

router = APIRouter(prefix="/v1/admin/route-center", tags=["route-center"])

_svc = RouteCenterService()
Ctx = Annotated[AdminContext, Depends(get_admin_context)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

READ = "routes_read"
WRITE = "routes"
DISPATCH = "routes_dispatch"


def _guard(ctx: AdminContext, module: str) -> None:
    try:
        require_module(ctx, module)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _handle(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    raise exc


@router.get("/meta")
def meta(ctx: Ctx) -> dict:
    _guard(ctx, READ)
    from porterchain_api.admin_engine.route_center_service import PLAN_STATUSES, STRATEGIES, VEHICLE_CLASSES

    return {
        "statuses": list(PLAN_STATUSES),
        "strategies": list(STRATEGIES),
        "vehicle_classes": list(VEHICLE_CLASSES),
    }


@router.get("/dashboard", response_model=RouteCenterDashboard)
def dashboard(ctx: Ctx, db: Session = Depends(get_db)) -> RouteCenterDashboard:
    _guard(ctx, READ)
    return RouteCenterDashboard(**_svc.dashboard(db))


@router.get("/planning-queue")
def planning_queue(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, READ)
    return _svc.planning_queue(db)


@router.get("/plans")
def list_plans(
    ctx: Ctx,
    db: Session = Depends(get_db),
    status: str | None = None,
    search: str | None = None,
    limit: int = Query(100, le=500),
) -> list[dict]:
    _guard(ctx, READ)
    return _svc.list_plans(db, status=status, search=search, limit=limit)


@router.get("/plans/{plan_id}")
def get_plan(ctx: Ctx, plan_id: str, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, READ)
    try:
        return _svc.get_plan(db, plan_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/plans")
def create_plan(ctx: Ctx, body: RoutePlanCreate, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, WRITE)
    return _svc.create_plan(
        db,
        ctx,
        name=body.name,
        order_ids=body.order_ids,
        strategy=body.strategy,
        zone=body.zone,
        template_id=body.template_id,
    )


@router.patch("/plans/{plan_id}")
def update_plan(ctx: Ctx, plan_id: str, body: RoutePlanUpdate, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, WRITE)
    try:
        return _svc.update_plan(
            db,
            ctx,
            plan_id,
            name=body.name,
            order_ids=body.order_ids,
            stops=body.stops,
            strategy=body.strategy,
            driver_id=body.driver_id,
            vehicle_id=body.vehicle_id,
        )
    except (LookupError, ValueError) as exc:
        raise _handle(exc) from exc


@router.post("/plans/{plan_id}/clone")
def clone_plan(ctx: Ctx, plan_id: str, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, WRITE)
    try:
        return _svc.clone_plan(db, ctx, plan_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/plans/merge")
def merge_plans(ctx: Ctx, body: RoutePlanMerge, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, WRITE)
    try:
        return _svc.merge_plans(db, ctx, body.plan_ids, body.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/plans/{plan_id}/split")
def split_plan(ctx: Ctx, plan_id: str, body: RoutePlanSplit, db: Session = Depends(get_db)) -> list[dict]:
    _guard(ctx, WRITE)
    try:
        return _svc.split_plan(db, ctx, plan_id, body.groups)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/plans/{plan_id}/optimize")
def optimize_plan(
    ctx: Ctx,
    plan_id: str,
    settings: SettingsDep,
    body: RouteOptimizeRequest,
    db: Session = Depends(get_db),
) -> dict:
    _guard(ctx, WRITE)
    try:
        return _svc.optimize_plan(
            db, settings, ctx, plan_id, strategy=body.strategy, engine=body.engine
        )
    except (LookupError, ValueError) as exc:
        raise _handle(exc) from exc


@router.post("/plans/{plan_id}/simulate")
def simulate_plan(
    ctx: Ctx,
    plan_id: str,
    settings: SettingsDep,
    db: Session = Depends(get_db),
) -> dict:
    _guard(ctx, READ)
    try:
        return _svc.simulate_plan(db, settings, plan_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/plans/{plan_id}/recommendations")
def recommendations(ctx: Ctx, plan_id: str, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, READ)
    try:
        return _svc.smart_recommendations(db, plan_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/plans/{plan_id}/dispatch")
def dispatch_plan(
    ctx: Ctx,
    plan_id: str,
    settings: SettingsDep,
    body: RouteDispatchRequest,
    db: Session = Depends(get_db),
) -> dict:
    _guard(ctx, DISPATCH)
    try:
        return _svc.dispatch_plan(
            db,
            settings,
            ctx,
            plan_id,
            driver_id=body.driver_id,
            vehicle_id=body.vehicle_id,
            approve=body.approve,
        )
    except (LookupError, PermissionError) as exc:
        raise _handle(exc) from exc


@router.post("/dispatch/bulk")
def bulk_dispatch(
    ctx: Ctx,
    settings: SettingsDep,
    body: RouteBulkDispatchRequest,
    db: Session = Depends(get_db),
) -> list[dict]:
    _guard(ctx, DISPATCH)
    return _svc.bulk_dispatch(db, settings, ctx, body.plan_ids, body.driver_id)


@router.post("/plans/{plan_id}/pause")
def pause_plan(ctx: Ctx, plan_id: str, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, DISPATCH)
    try:
        return _svc.pause_plan(db, ctx, plan_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/plans/{plan_id}/resume")
def resume_plan(ctx: Ctx, plan_id: str, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, DISPATCH)
    try:
        return _svc.resume_plan(db, ctx, plan_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/plans/{plan_id}/cancel")
def cancel_plan(ctx: Ctx, plan_id: str, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, DISPATCH)
    try:
        return _svc.cancel_plan(db, ctx, plan_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/templates")
def list_templates(ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    _guard(ctx, READ)
    return _svc.list_templates(db)


@router.post("/plans/{plan_id}/save-template")
def save_template(
    ctx: Ctx, plan_id: str, body: RouteTemplateSave, db: Session = Depends(get_db)
) -> dict:
    _guard(ctx, WRITE)
    try:
        return _svc.save_template_from_plan(db, ctx, plan_id, body.name, body.template_type)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/templates/{template_id}/create-plan")
def create_from_template(
    ctx: Ctx,
    template_id: str,
    body: RouteTemplateCreatePlan,
    db: Session = Depends(get_db),
) -> dict:
    _guard(ctx, WRITE)
    try:
        return _svc.create_plan_from_template(db, ctx, template_id, name=body.name)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/analytics")
def analytics(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, READ)
    return _svc.analytics(db)


@router.get("/history")
def history(ctx: Ctx, db: Session = Depends(get_db), limit: int = Query(50, le=200)) -> list[dict]:
    _guard(ctx, READ)
    return _svc.history(db, limit=limit)


@router.get("/live-execution")
def live_execution(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Live fleet snapshot — reuses LiveMapService (Google Maps visualization in admin)."""
    _guard(ctx, READ)
    return _svc.live_execution_snapshot(db)
