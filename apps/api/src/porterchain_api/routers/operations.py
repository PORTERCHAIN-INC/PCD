"""Operations Control Tower API — /v1/admin/operations/*

Reads the Porterchain order mirror, exceptions, claims, SLA and activity.
Driver assignment / dispatch execution is bridged to Fleetbase through the
existing /v1/admin/dispatch endpoints + adapter (never called directly here).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.control_tower_service import ControlTowerService
from porterchain_api.admin_engine.dispatch_queue_optimizer import DispatchQueueOptimizer
from porterchain_api.admin_engine.live_map_service import LiveMapService
from porterchain_api.admin_engine.operations_service import AdminOperationsService
from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.auth.clerk import verify_clerk_token
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import SessionLocal, get_db
from porterchain_api.schemas_live_map import LiveMapFilters

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/admin/operations", tags=["operations"])

_ct = ControlTowerService()
_live_map = LiveMapService()
_ops = AdminOperationsService()
_optimizer = DispatchQueueOptimizer()
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


@router.post("/board/move")
def board_move(body: BoardMoveBody, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "dispatch")
    try:
        return _ct.move_board_order(db, ctx, body.order_id, body.to_column)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/orders")
def active_orders(ctx: Ctx, db: Session = Depends(get_db), search: str | None = None) -> list[dict]:
    _guard(ctx, "dispatch_read")
    return _ct.active_orders(db, search=search)


@router.get("/queue")
def queue(ctx: Ctx, db: Session = Depends(get_db)) -> list[dict]:
    _guard(ctx, "dispatch_read")
    return _ct.queue(db)


class OptimizeQueueBody(BaseModel):
    order_ids: list[str]
    strategy: str | None = "balanced"
    engine: str = "valhalla"


class AssignBatchBody(BaseModel):
    plan_id: str
    driver_id: str
    order_ids: list[str] | None = None


@router.post("/queue/optimize")
def optimize_queue(
    body: OptimizeQueueBody,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    _guard(ctx, "dispatch")
    try:
        return _optimizer.optimize(
            db,
            settings,
            ctx,
            body.order_ids,
            strategy=body.strategy or "balanced",
            engine=body.engine,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/queue/assign-batch")
def assign_batch(
    body: AssignBatchBody,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    _guard(ctx, "dispatch")
    try:
        return _ops.assign_batch(
            db,
            settings,
            ctx,
            plan_id=body.plan_id,
            driver_id=body.driver_id,
            order_ids=body.order_ids,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    """Legacy snapshot shape for Operations Control Tower map tab."""
    _guard(ctx, "map")
    snap = _live_map.snapshot(db)
    seen_orders: set[str] = set()
    orders = []
    for o in snap["orders"]:
        if o["order_id"] in seen_orders:
            continue
        seen_orders.add(o["order_id"])
        orders.append(
            {
                "order_id": o["order_id"],
                "tracking": o["tracking_number"],
                "state": o["state"],
                "pickup": {},
                "dropoff": {},
            }
        )
    return {
        "drivers": [
            {"id": d["id"], "name": d["name"], "status": d["availability"], "online": d["online"]}
            for d in snap["drivers"]
        ],
        "orders": orders,
        "fleetbase_note": "GPS positions synced via Porterchain API bridge — not Fleetbase UI",
    }


@router.get("/live-map")
def live_map_full(
    ctx: Ctx,
    db: Session = Depends(get_db),
    driver_status: str | None = None,
    vehicle_type: str | None = None,
    merchant_id: str | None = None,
    city: str | None = None,
    region: str | None = None,
    priority: str | None = None,
    delivery_status: str | None = None,
    date: str | None = None,
    service_area: str | None = None,
    vehicle_capacity_min_kg: float | None = None,
    online_only: bool | None = None,
) -> dict:
    _guard(ctx, "map")
    filters = LiveMapFilters(
        driver_status=driver_status.split(",") if driver_status else None,
        vehicle_type=vehicle_type.split(",") if vehicle_type else None,
        merchant_id=merchant_id,
        city=city,
        region=region,
        priority=priority,  # type: ignore[arg-type]
        delivery_status=delivery_status.split(",") if delivery_status else None,
        date=date,
        service_area=service_area,
        vehicle_capacity_min_kg=vehicle_capacity_min_kg,
        online_only=online_only,
    )
    return _live_map.snapshot(db, filters=filters)


@router.get("/live-map/search")
def live_map_search(ctx: Ctx, db: Session = Depends(get_db), q: str = Query(min_length=2)) -> list[dict]:
    _guard(ctx, "map")
    return _live_map.search(db, q)


@router.get("/live-map/detail/{entity_type}/{entity_id}")
def live_map_detail(ctx: Ctx, entity_type: str, entity_id: str, db: Session = Depends(get_db)) -> dict:
    _guard(ctx, "map")
    try:
        return _live_map.entity_detail(db, entity_type, entity_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="entity_not_found") from exc


@router.get("/live-map/playback")
def live_map_playback(
    ctx: Ctx,
    db: Session = Depends(get_db),
    date: str = Query(..., alias="date"),
    driver_id: str | None = None,
) -> dict:
    _guard(ctx, "map")
    try:
        return _live_map.playback(db, day=date, driver_id=driver_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/live-map/nearest-drivers")
def live_map_nearest(
    ctx: Ctx,
    db: Session = Depends(get_db),
    lat: float = Query(...),
    lng: float = Query(...),
    limit: int = Query(5, ge=1, le=20),
) -> list[dict]:
    _guard(ctx, "map")
    return _live_map.nearest_drivers(db, lat=lat, lng=lng, limit=limit)


@router.websocket("/live-map/ws")
async def live_map_ws(
    websocket: WebSocket,
    token: str = Query(...),
    settings: Settings = Depends(get_settings),
) -> None:
    """Push live map snapshots every 5s. Auth via Clerk JWT query param."""
    try:
        await verify_clerk_token(token, settings)
    except HTTPException:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    try:
        while True:
            db = SessionLocal()
            try:
                payload = _live_map.snapshot(db)
                await websocket.send_json({"type": "snapshot", "data": payload})
            finally:
                db.close()
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        logger.debug("live_map websocket disconnected")
    except Exception:
        logger.exception("live_map websocket error")
        await websocket.close(code=1011)


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
