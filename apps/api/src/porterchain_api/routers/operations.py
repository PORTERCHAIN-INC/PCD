"""Operations Control Tower API — /v1/admin/operations/*

Reads the Porterchain order mirror, exceptions, claims, SLA and activity.
Driver assignment / dispatch execution is bridged to Fleetbase through the
existing /v1/admin/dispatch endpoints + adapter (never called directly here).
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.control_tower_service import ControlTowerService
from porterchain_api.admin_engine.dispatch_suggestions_service import (
    DispatchSuggestionsService,
)
from porterchain_api.admin_engine.live_map_service import LiveMapService
from porterchain_api.admin_engine.dispatcher_copilot_service import DispatcherCopilotService
from porterchain_api.admin_engine.orchestrator_ops_service import OrchestratorOpsService
from porterchain_api.admin_engine.scheduled_batches_service import ScheduledBatchesService
from porterchain_api.admin_engine.utilization_service import UtilizationService
from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import get_db
from porterchain_api.platform.pagination import DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/admin/operations", tags=["operations"])

_ct = ControlTowerService()
_suggestions = DispatchSuggestionsService()
_live_map = LiveMapService()
_batches = ScheduledBatchesService()
_orch = OrchestratorOpsService()
_copilot = DispatcherCopilotService()
_utilization = UtilizationService()
Ctx = Annotated[AdminContext, Depends(get_admin_context)]


def _guard(ctx: AdminContext, module: str) -> None:
    try:
        require_module(ctx, module)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/stats")
def stats(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "dispatch_read")
    return _ct.stats(db)


@router.get("/board")
def board(ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    _guard(ctx, "dispatch_read")
    return _ct.board(db)


class BoardMoveBody(BaseModel):
    order_id: str
    to_column: str
    reason: str | None = None


@router.post("/board/move")
def board_move(body: BoardMoveBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "dispatch")
    try:
        return _ct.move_board_order(
            db, ctx, body.order_id, body.to_column, reason=body.reason
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/orders")
def active_orders(
    ctx: Ctx,
    db: Session = Depends(get_db),
    search: str | None = None,
    limit: int = Query(DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT),
) -> list[dict]:
    _guard(ctx, "dispatch_read")
    return _ct.active_orders(db, search=search, limit=limit)


@router.get("/queue")
def queue(
    ctx: Ctx,
    db: Session = Depends(get_db),
    limit: int = Query(200, ge=1, le=MAX_LIST_LIMIT),
) -> list[dict]:
    _guard(ctx, "dispatch_read")
    return _ct.queue(db, limit=limit)


@router.get("/assignable-drivers")
def assignable_drivers(ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    _guard(ctx, "dispatch_read")
    return _ct.assignable_drivers(db)


@router.get("/orders/{order_id}/driver-suggestions")
def driver_suggestions(order_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Ranked driver candidates for one order — ETA/load/rating/capability."""
    _guard(ctx, "dispatch_read")
    try:
        return _suggestions.suggest(db, order_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/live-map")
def live_map(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Adapter-fed driver positions + in-flight order stops (Google tiles only)."""
    _guard(ctx, "dispatch_read")
    return _live_map.snapshot(db)


@router.get("/orders/{order_id}/route-geometry")
def order_route_geometry(order_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Valhalla route polyline for one order; straight-leg fallback labeled 'direct'."""
    _guard(ctx, "dispatch_read")
    try:
        return _live_map.route_geometry(db, order_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/orders/{order_id}/playback")
def order_playback(order_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Adapter-fed Fleetbase position breadcrumbs for client-side playback."""
    _guard(ctx, "dispatch_read")
    try:
        return _live_map.playback(db, order_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/utilization")
def utilization(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Shift/staffing snapshot — Fleetbase online + PC shifts + PC order load."""
    _guard(ctx, "dispatch_read")
    return _utilization.snapshot(db)


@router.get("/exceptions")
def exceptions(
    ctx: Ctx,
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=MAX_LIST_LIMIT),
) -> list[dict]:
    _guard(ctx, "dispatch_read")
    return _ct.exceptions(db, limit=limit)


class ExceptionResolveBody(BaseModel):
    note: str | None = None


@router.post("/exceptions/{exception_id}/acknowledge")
def exception_acknowledge(exception_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "dispatch")
    try:
        return _ct.acknowledge_exception(db, ctx, exception_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/exceptions/{exception_id}/resolve")
def exception_resolve(
    exception_id: str, body: ExceptionResolveBody, ctx: Ctx, db: Session = Depends(get_db)
) -> dict:
    _guard(ctx, "dispatch")
    try:
        return _ct.resolve_exception(db, ctx, exception_id, note=body.note)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/exceptions/{exception_id}/retry")
def exception_retry(exception_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Re-queue the failed order for dispatch and resolve the exception."""
    _guard(ctx, "dispatch")
    try:
        return _ct.retry_exception_dispatch(db, ctx, exception_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/scheduled-batches")
def scheduled_batches(
    ctx: Ctx,
    db: Session = Depends(get_db),
    day: date | None = Query(None, description="UTC calendar day YYYY-MM-DD"),
    merchant_id: str | None = None,
) -> dict:
    """Merchant pickup batches for a day (PC planning view; not Fleetbase manifests)."""
    _guard(ctx, "dispatch_read")
    return _batches.list_batches(db, day=day, merchant_id=merchant_id)


@router.get("/manifests")
def manifests(
    ctx: Ctx,
    db: Session = Depends(get_db),
    scheduled_date: str | None = Query(None, description="YYYY-MM-DD"),
    status: str | None = None,
) -> dict:
    """Committed Fleetbase manifests (adapter → ManifestController)."""
    _guard(ctx, "dispatch_read")
    return _batches.list_manifests(db, scheduled_date=scheduled_date, status=status)


@router.get("/manifests/{manifest_id}")
def manifest_detail(manifest_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "dispatch_read")
    row = _batches.get_manifest(db, manifest_id)
    if not row:
        raise HTTPException(status_code=404, detail="manifest_not_found")
    return row


class OptimizeRunBody(BaseModel):
    order_ids: list[str] | None = None
    mode: str = "allocate"
    engine: str | None = "greedy"


class OptimizeCommitBody(BaseModel):
    assignments: list[dict]
    scheduled_date: str | None = None


@router.get("/optimize/pool")
def optimize_pool(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Synced orders eligible for Fleetbase orchestrator run."""
    _guard(ctx, "dispatch_read")
    return _orch.pool(db)


@router.get("/optimize/engines")
def optimize_engines(ctx: Ctx) -> dict:
    _guard(ctx, "dispatch_read")
    return {"engines": _orch.engines()}


@router.post("/optimize/run")
def optimize_run(body: OptimizeRunBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Preview plan via Fleetbase OrchestratorService (no commit)."""
    _guard(ctx, "dispatch")
    return _orch.run(db, order_ids=body.order_ids, mode=body.mode, engine=body.engine)


@router.post("/optimize/commit")
def optimize_commit(body: OptimizeCommitBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Commit plan → Fleetbase manifests (ManifestController create path)."""
    _guard(ctx, "dispatch")
    if not body.assignments:
        raise HTTPException(status_code=400, detail="assignments_required")
    return _orch.commit(db, assignments=body.assignments, scheduled_date=body.scheduled_date)


@router.get("/sla")
def sla(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "dispatch_read")
    return _ct.sla_monitor(db)


@router.get("/activity")
def activity(
    ctx: Ctx,
    db: Session = Depends(get_db),
    limit: int = Query(60, ge=1, le=MAX_LIST_LIMIT),
) -> list[dict]:
    _guard(ctx, "dispatch_read")
    return _ct.live_activity(db, limit=limit)


@router.get("/ai")
def ai_ops(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "dispatch_read")
    return _ct.ai_ops(db)


@router.get("/copilot")
def copilot_recommendations(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Next-best-action recommendations (assign) with savings vs next-best driver."""
    _guard(ctx, "dispatch_read")
    return _copilot.recommendations(db, ctx)


@router.get("/copilot/audit")
def copilot_audit(
    ctx: Ctx,
    db: Session = Depends(get_db),
    limit: int = Query(40, ge=1, le=100),
) -> list[dict]:
    _guard(ctx, "dispatch_read")
    return _copilot.audit_trail(db, limit=limit)


class CopilotActionBody(BaseModel):
    action_id: str
    order_id: str
    driver_id: str | None = None
    reason: str | None = None


@router.post("/copilot/accept")
def copilot_accept(body: CopilotActionBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "dispatch")
    if not body.driver_id:
        raise HTTPException(status_code=400, detail="driver_id_required")
    try:
        return _copilot.accept(
            db,
            ctx,
            action_id=body.action_id,
            order_id=body.order_id,
            driver_id=body.driver_id,
            modified=False,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/copilot/modify")
def copilot_modify(body: CopilotActionBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Accept with an alternate driver — audited as override."""
    _guard(ctx, "dispatch")
    if not body.driver_id:
        raise HTTPException(status_code=400, detail="driver_id_required")
    try:
        return _copilot.accept(
            db,
            ctx,
            action_id=body.action_id,
            order_id=body.order_id,
            driver_id=body.driver_id,
            modified=True,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/copilot/dismiss")
def copilot_dismiss(body: CopilotActionBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "dispatch")
    return _copilot.dismiss(
        db, ctx, action_id=body.action_id, order_id=body.order_id, reason=body.reason
    )


@router.get("/search")
def ops_search(
    ctx: Ctx,
    db: Session = Depends(get_db),
    q: str = Query(..., min_length=1, max_length=80),
    limit: int = Query(12, ge=1, le=40),
) -> dict:
    """Cmd+K jump targets — orders + drivers (PC mirror only)."""
    _guard(ctx, "dispatch_read")
    from porterchain_api.admin_models import Driver
    from porterchain_api.models import Order

    needle = q.strip()
    like = f"%{needle}%"
    orders = (
        db.query(Order)
        .filter(
            (Order.tracking_number.ilike(like))
            | (Order.order_number.ilike(like))
            | (Order.id == needle)
        )
        .order_by(Order.created_at.desc())
        .limit(limit)
        .all()
    )
    drivers = (
        db.query(Driver)
        .filter(
            (Driver.full_name.ilike(like))
            | (Driver.email.ilike(like))
            | (Driver.id == needle)
        )
        .limit(limit)
        .all()
    )
    return {
        "q": needle,
        "orders": [
            {
                "id": o.id,
                "tracking_number": o.tracking_number,
                "order_number": o.order_number,
                "state": o.state,
                "kind": "order",
            }
            for o in orders
        ],
        "drivers": [
            {
                "id": d.id,
                "name": d.full_name,
                "online": bool(d.is_online) or d.availability == "online",
                "kind": "driver",
            }
            for d in drivers
        ],
    }


@router.get("/sync/health")
def sync_health(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "dispatch_read")
    return _ct.sync_health(db)


@router.get("/queues")
def queue_depths_endpoint(ctx: Ctx) -> dict:
    """Redis queue depths for ops control tower."""
    _guard(ctx, "dispatch_read")
    from porterchain_shared.queue.publisher import queue_depths

    return {"depths": queue_depths()}


@router.post("/sync/process")
def sync_process(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "dispatch")
    from porterchain_api.config import get_settings
    from porterchain_api.fleetbase_engine import BookingSyncService

    return BookingSyncService().process_retry_queue(db, get_settings())


@router.post("/sync/requeue/{job_id}")
def sync_requeue(job_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "dispatch")
    from porterchain_api.fleetbase_engine import ErrorQueue

    job = ErrorQueue.requeue(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_not_found")
    return {"ok": True, "id": job.id, "status": job.status}
