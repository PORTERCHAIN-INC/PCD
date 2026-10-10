"""Operations Control Tower API — /v1/admin/operations/* (mirror, SLA, dispatch)."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.control_tower_service import ControlTowerService
from porterchain_api.admin_engine.dispatch_suggestions_service import (
    DispatchSuggestionsService,
)
from porterchain_api.admin_engine.live_map_service import LiveMapService
from porterchain_api.admin_engine.dispatcher_copilot_service import DispatcherCopilotService
from porterchain_api.admin_engine.operations_service import AdminOperationsService
from porterchain_api.admin_engine.orchestrator_ops_service import OrchestratorOpsService
from porterchain_api.admin_engine.scheduled_batches_service import ScheduledBatchesService
from porterchain_api.admin_engine.utilization_service import UtilizationService
from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import get_db
from porterchain_api.platform.pagination import DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT
from porterchain_api.config import Settings
from porterchain_api.routers.admin._deps import _order_item, get_settings
from porterchain_api.schemas_admin import (
    AssignDriverRequest,
    BoardMoveBody,
    CopilotActionBody,
    CopilotLlmSuggestBody,
    ExceptionResolveBody,
    OptimizeCommitBody,
    OptimizeRunBody,
    OrderAdminItem,
)

dispatch_router = APIRouter(prefix="/v1/admin", tags=["dispatch"])

router = APIRouter(prefix="/v1/admin/operations", tags=["operations"])

_ct = ControlTowerService()
_suggestions = DispatchSuggestionsService()
_live_map = LiveMapService()
_batches = ScheduledBatchesService()
_orch = OrchestratorOpsService()
_copilot = DispatcherCopilotService()
_utilization = UtilizationService()
_ops = AdminOperationsService()
Ctx = Annotated[AdminContext, Depends(get_admin_context)]


def _invoke(ctx: AdminContext, module: str, fn, *args, **kwargs):
    try:
        require_module(ctx, module)
        return fn(*args, **kwargs)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/stats")
def stats(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "dispatch_read", _ct.stats, db)


@router.get("/board")
def board(ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    return _invoke(ctx, "dispatch_read", _ct.board, db)


@router.post("/board/move")
def board_move(body: BoardMoveBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(
        ctx, "dispatch", _ct.move_board_order, db, ctx, body.order_id, body.to_column, reason=body.reason
    )


@router.get("/orders")
def active_orders(
    ctx: Ctx,
    db: Session = Depends(get_db),
    search: str | None = None,
    limit: int = Query(DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT),
) -> list[dict]:
    return _invoke(ctx, "dispatch_read", _ct.active_orders, db, search=search, limit=limit)


@router.get("/queue")
def queue(
    ctx: Ctx,
    db: Session = Depends(get_db),
    limit: int = Query(200, ge=1, le=MAX_LIST_LIMIT),
) -> list[dict]:
    return _invoke(ctx, "dispatch_read", _ct.queue, db, limit=limit)


@router.get("/assignable-drivers")
def assignable_drivers(ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    return _invoke(ctx, "dispatch_read", _ct.assignable_drivers, db)


@router.get("/orders/{order_id}/driver-suggestions")
def driver_suggestions(order_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Ranked driver candidates for one order — ETA/load/rating/capability."""
    return _invoke(ctx, "dispatch_read", _suggestions.suggest, db, order_id)


@router.get("/live-map")
def live_map(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Adapter-fed driver positions + in-flight order stops (Google tiles only)."""
    return _invoke(ctx, "dispatch_read", _live_map.snapshot, db)


@router.get("/orders/{order_id}/route-geometry")
def order_route_geometry(order_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Valhalla route polyline for one order; straight-leg fallback labeled 'direct'."""
    return _invoke(ctx, "dispatch_read", _live_map.route_geometry, db, order_id)


@router.get("/orders/{order_id}/playback")
def order_playback(order_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Driver position breadcrumbs for client-side playback."""
    return _invoke(ctx, "dispatch_read", _live_map.playback, db, order_id)


@router.get("/utilization")
def utilization(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Shift/staffing snapshot — open shifts + order load."""
    return _invoke(ctx, "dispatch_read", _utilization.snapshot, db)


@router.get("/exceptions")
def exceptions(
    ctx: Ctx,
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=MAX_LIST_LIMIT),
) -> list[dict]:
    return _invoke(ctx, "dispatch_read", _ct.exceptions, db, limit=limit)


@router.post("/exceptions/{exception_id}/acknowledge")
def exception_acknowledge(exception_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "dispatch", _ct.acknowledge_exception, db, ctx, exception_id)


@router.post("/exceptions/{exception_id}/resolve")
def exception_resolve(
    exception_id: str, body: ExceptionResolveBody, ctx: Ctx, db: Session = Depends(get_db)
) -> dict:
    return _invoke(ctx, "dispatch", _ct.resolve_exception, db, ctx, exception_id, note=body.note)


@router.post("/exceptions/{exception_id}/retry")
def exception_retry(exception_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Re-queue the failed order for dispatch and resolve the exception."""
    return _invoke(ctx, "dispatch", _ct.retry_exception_dispatch, db, ctx, exception_id)


@router.get("/scheduled-batches")
def scheduled_batches(
    ctx: Ctx,
    db: Session = Depends(get_db),
    day: date | None = Query(None, description="UTC calendar day YYYY-MM-DD"),
    merchant_id: str | None = None,
) -> dict:
    """Merchant pickup batches for a day (planning view)."""
    return _invoke(ctx, "dispatch_read", _batches.list_batches, db, day=day, merchant_id=merchant_id)


@router.get("/manifests")
def manifests(
    ctx: Ctx,
    db: Session = Depends(get_db),
    scheduled_date: str | None = Query(None, description="YYYY-MM-DD"),
    status: str | None = None,
) -> dict:
    """Committed route manifests."""
    return _invoke(
        ctx, "dispatch_read", _batches.list_manifests, db, scheduled_date=scheduled_date, status=status
    )


@router.get("/manifests/{manifest_id}")
def manifest_detail(manifest_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    row = _invoke(ctx, "dispatch_read", _batches.get_manifest, db, manifest_id)
    if not row:
        raise HTTPException(status_code=404, detail="manifest_not_found")
    return row


@router.get("/optimize/pool")
def optimize_pool(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Orders eligible for the PorterChain day-plan preview."""
    return _invoke(ctx, "dispatch_read", _orch.pool, db)


@router.get("/optimize/engines")
def optimize_engines(ctx: Ctx) -> dict:
    return _invoke(ctx, "dispatch_read", lambda: {"engines": _orch.engines()})


@router.post("/optimize/run")
def optimize_run(body: OptimizeRunBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Queue a PorterChain day-plan preview. Does not wait on the solver."""
    return _invoke(
        ctx,
        "dispatch",
        _orch.enqueue_run,
        db,
        order_ids=body.order_ids,
        mode=body.mode,
        engine=body.engine,
        shape=body.shape,
        merchant_id=body.merchant_id,
        vehicle_ids=body.vehicle_ids,
        driver_ids=body.driver_ids,
        pc_driver_id=getattr(body, "pc_driver_id", None),
        offset=body.offset,
    )


@router.get("/optimize/runs/{run_id}")
def optimize_run_status(run_id: str, ctx: Ctx) -> dict:
    """Poll queued preview: pending | ready | error."""
    row = _invoke(ctx, "dispatch_read", _orch.get_run, run_id)
    if not row:
        raise HTTPException(status_code=404, detail="optimize_run_not_found")
    return row


@router.post("/optimize/commit")
def optimize_commit(body: OptimizeCommitBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Accept the stored day plan into sequence_store."""
    from porterchain_driver.sequence_store import SequenceConflictError

    try:
        return _invoke(
            ctx,
            "dispatch",
            _orch.commit,
            db,
            assignments=body.assignments,
            scheduled_date=body.scheduled_date,
            run_id=body.run_id,
            expected_sequence_version=body.expected_sequence_version,
            pc_driver_id=body.pc_driver_id,
        )
    except SequenceConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "sequence_version_conflict",
                "current_version": exc.current_version,
                "expected_version": exc.expected_version,
            },
        ) from exc


@router.get("/sla")
def sla(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "dispatch_read", _ct.sla_monitor, db)


@router.get("/activity")
def activity(
    ctx: Ctx,
    db: Session = Depends(get_db),
    limit: int = Query(60, ge=1, le=MAX_LIST_LIMIT),
) -> list[dict]:
    return _invoke(ctx, "dispatch_read", _ct.live_activity, db, limit=limit)


@router.get("/ai")
def ai_ops(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "dispatch_read", _ct.ai_ops, db)


@router.get("/copilot")
def copilot_recommendations(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Next-best-action recommendations (assign) with savings vs next-best driver."""
    return _invoke(ctx, "dispatch_read", _copilot.recommendations, db, ctx)


@router.post("/copilot/llm")
def copilot_llm_suggest(
    body: CopilotLlmSuggestBody,
    ctx: Ctx,
    db: Session = Depends(get_db),
) -> dict:
    """Phase-2 LLM ops suggestions via NVIDIA NIM when configured (read-only)."""
    from porterchain_api.intelligence_engine.copilot_service import suggest_ops_action_committed

    def _run():
        flags = {
            "intelligence": body.enable_intelligence,
            "ai_dispatch": body.enable_intelligence,
        }
        return suggest_ops_action_committed(
            body.context,
            flags=flags,
            db=db,
            actor_type="admin",
            actor_id=getattr(ctx.user, "id", None),
            merchant_id=body.merchant_id,
            include_sla_queue=body.include_sla_queue,
        )

    return _invoke(ctx, "dispatch_read", _run)


@router.get("/copilot/audit")
def copilot_audit(
    ctx: Ctx,
    db: Session = Depends(get_db),
    limit: int = Query(40, ge=1, le=100),
) -> list[dict]:
    return _invoke(ctx, "dispatch_read", _copilot.audit_trail, db, limit=limit)


@router.post("/copilot/accept")
def copilot_accept(body: CopilotActionBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(
        ctx,
        "dispatch",
        _copilot.accept,
        db,
        ctx,
        action_id=body.action_id,
        order_id=body.order_id,
        driver_id=body.driver_id,
        modified=False,
    )


@router.post("/copilot/modify")
def copilot_modify(body: CopilotActionBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    """Accept with an alternate driver — audited as override."""
    return _invoke(
        ctx,
        "dispatch",
        _copilot.accept,
        db,
        ctx,
        action_id=body.action_id,
        order_id=body.order_id,
        driver_id=body.driver_id,
        modified=True,
    )


@router.post("/copilot/dismiss")
def copilot_dismiss(body: CopilotActionBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(
        ctx, "dispatch", _copilot.dismiss, db, ctx, action_id=body.action_id, order_id=body.order_id, reason=body.reason
    )


@router.get("/search")
def ops_search(
    ctx: Ctx,
    db: Session = Depends(get_db),
    q: str = Query(..., min_length=1, max_length=80),
    limit: int = Query(12, ge=1, le=40),
) -> dict:
    """Cmd+K jump targets — orders + drivers (PC mirror only)."""
    return _invoke(ctx, "dispatch_read", _ct.ops_search, db, q=q, limit=limit)


@router.get("/sync/health")
def sync_health(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "dispatch_read", _ct.sync_health, db)


@router.get("/queues")
def queue_depths_endpoint(ctx: Ctx) -> dict:
    """Redis queue depths for ops control tower."""
    return _invoke(ctx, "dispatch_read", _ops.queue_depths_snapshot)


@router.post("/sync/process")
def sync_process(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "dispatch", _ops.process_sync_retry, db, limit=1)


@router.post("/sync/requeue/{job_id}")
def sync_requeue(job_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "dispatch", _ops.requeue_sync_job, db, job_id)


@dispatch_router.post("/dispatch/orders/{order_id}/assign", response_model=OrderAdminItem)
def assign_driver(
    order_id: str,
    body: AssignDriverRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OrderAdminItem:
    require_module(ctx, "dispatch")
    try:
        order = _ops.assign_driver(db, settings, ctx, order_id, body.driver_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _order_item(order)


from porterchain_api.routers import operations_maps  # noqa: E402,F401  (registers map routes)
