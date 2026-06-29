"""Operations Control Tower API — /v1/admin/operations/*

Reads the Porterchain order mirror, exceptions, claims, SLA and activity.
Driver assignment / dispatch execution is bridged to Fleetbase through the
existing /v1/admin/dispatch endpoints + adapter (never called directly here).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.control_tower_service import ControlTowerService
from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import get_db

router = APIRouter(prefix="/v1/admin/operations", tags=["operations"])

_ct = ControlTowerService()
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


@router.get("/orders")
def active_orders(ctx: Ctx, db: Session = Depends(get_db), search: str | None = None) -> list[dict]:
    _guard(ctx, "dispatch_read")
    return _ct.active_orders(db, search=search)


@router.get("/queue")
def queue(ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    _guard(ctx, "dispatch_read")
    return _ct.queue(db)


@router.get("/assignable-drivers")
def assignable_drivers(ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    _guard(ctx, "dispatch_read")
    return _ct.assignable_drivers(db)


@router.get("/exceptions")
def exceptions(ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    _guard(ctx, "dispatch_read")
    return _ct.exceptions(db)


@router.get("/sla")
def sla(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "dispatch_read")
    return _ct.sla_monitor(db)


@router.get("/activity")
def activity(ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    _guard(ctx, "dispatch_read")
    return _ct.live_activity(db)


@router.get("/ai")
def ai_ops(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "dispatch_read")
    return _ct.ai_ops(db)


@router.get("/map")
def live_map(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "map")
    from porterchain_api.admin_engine.operations_service import AdminOperationsService

    return AdminOperationsService().live_map_snapshot(db)


# --------------------------------------------------------------------------- #
# Fleetbase sync engine — queue health + recovery
# --------------------------------------------------------------------------- #
@router.get("/sync/health")
def sync_health(ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "dispatch_read")
    from porterchain_api.fleetbase_engine import ErrorQueue
    from porterchain_api.fleetbase_models import FleetbaseSyncAudit

    recent = (
        db.query(FleetbaseSyncAudit)
        .order_by(FleetbaseSyncAudit.created_at.desc())
        .limit(40)
        .all()
    )
    return {
        "queue": ErrorQueue.stats(db),
        "dead_letters": [
            {"id": j.id, "kind": j.kind, "direction": j.direction, "order_id": j.order_id, "attempts": j.attempts, "last_error": j.last_error}
            for j in ErrorQueue.list_dead(db)
        ],
        "recent_audit": [
            {
                "direction": a.direction, "kind": a.kind, "status": a.status,
                "order_id": a.order_id, "message": a.message,
                "at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in recent
        ],
    }


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
