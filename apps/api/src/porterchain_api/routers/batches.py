"""Bulk delivery batches: merchant CSV upload + admin assignment (driver side: routers/driver/batches.py)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext, AdminRole
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.auth.merchant import get_merchant_context
from porterchain_api.batch_engine import service as svc
from porterchain_api.batch_engine.models import DeliveryBatch
from porterchain_api.db import db_transaction, get_db

merchant_router = APIRouter(prefix="/v1/merchant/batches", tags=["merchant-batches"])
admin_router = APIRouter(prefix="/v1/admin/batches", tags=["admin-batches"])
_OPS = (AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.DISPATCHER, AdminRole.FLEET_MANAGER)


class BatchBody(BaseModel):
    csv: str = Field(min_length=1, max_length=5_000_000)
    pickup_source: str = "shop"
    pickup_point: dict | None = None
    vehicle_class: str = "cargo_van"
    drivers: int = Field(1, ge=1, le=200)
    doc_flags: dict | None = None
    confirm_duplicates: bool = False


def _http(exc: Exception) -> HTTPException:
    code = 404 if isinstance(exc, LookupError) else 403 if isinstance(exc, PermissionError) else 422
    return HTTPException(status_code=code, detail=str(exc))


@merchant_router.post("")
def create(body: BatchBody, ctx=Depends(get_merchant_context), db: Session = Depends(get_db)):
    try:
        with db_transaction(db):
            b = svc.create_batch(db, str(ctx.merchant.id), body.csv, vehicle_class=body.vehicle_class,
                                 drivers=body.drivers, pickup_source=body.pickup_source,
                                 pickup_point=body.pickup_point, doc_flags=body.doc_flags,
                                 confirm_duplicates=body.confirm_duplicates)
            return svc.batch_out(db, b)
    except svc.DuplicateRows as exc:
        raise HTTPException(status_code=409, detail={"code": "duplicates_need_confirm",
                                                     "warnings": exc.warnings}) from exc
    except ValueError as exc:
        raise _http(exc) from exc


def _list(db: Session, merchant_id: str | None, limit: int) -> dict:
    q = db.query(DeliveryBatch)
    if merchant_id:
        q = q.filter(DeliveryBatch.merchant_id == merchant_id)
    rows = q.order_by(DeliveryBatch.created_at.desc()).limit(min(max(limit, 1), 200)).all()
    return {"batches": [{"id": b.id, "merchant_id": b.merchant_id, "status": b.status,
                         "parcels": (b.plan or {}).get("parcels"), "routes": (b.plan or {}).get("routes"), "waves": (b.plan or {}).get("waves"),
                         "pickup_docs": (b.plan or {}).get("pickup_docs") or [],
                         "created_at": b.created_at.isoformat() if b.created_at else None} for b in rows]}


@merchant_router.get("")
def merchant_list(limit: int = 50, ctx=Depends(get_merchant_context), db: Session = Depends(get_db)):
    return _list(db, str(ctx.merchant.id), limit)


@merchant_router.get("/{batch_id}")
def get(batch_id: str, ctx=Depends(get_merchant_context), db: Session = Depends(get_db)):
    b = db.get(DeliveryBatch, batch_id)
    if not b or b.merchant_id != str(ctx.merchant.id):
        raise HTTPException(status_code=404, detail="batch_not_found")
    return svc.batch_out(db, b)


def _ops(ctx: AdminContext) -> None:
    if ctx.role not in _OPS:
        raise HTTPException(status_code=403, detail="dispatch_role_required")


@merchant_router.get("/{batch_id}/edi/{kind}")
def merchant_edi(batch_id: str, kind: str, ctx=Depends(get_merchant_context), db: Session = Depends(get_db)):
    """Doc 84 Q7: the merchant downloads X12 214/856 for its own batch only."""
    from porterchain_api.ops_rules.edi_service import export_batch
    b = db.get(DeliveryBatch, batch_id)
    if not b or b.merchant_id != str(ctx.merchant.id):
        raise HTTPException(status_code=404, detail="batch_not_found")
    try:
        return export_batch(db, batch_id, kind, receiver=str(ctx.merchant.id)[:15])
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@admin_router.get("")
def admin_list(ctx: Annotated[AdminContext, Depends(get_admin_context)], limit: int = 50,
               merchant_id: str | None = None, db: Session = Depends(get_db)):
    _ops(ctx)
    return _list(db, merchant_id, limit)


_SCENARIOS = ("verification", "split_pickup", "cross_dock", "consolidate", "partial_pickup", "add_reverse_pickup",
              "failed_disposition", "reassign_oversize", "container_count", "stop_rules", "reassign_remaining",
              "resolve_windows")


@admin_router.post("/scenarios/{name}")
def scenario(name: str, body: dict, ctx: Annotated[AdminContext, Depends(get_admin_context)]):
    """Evaluate one scenario rule (read-only what-if for dispatch); body = the rule's keyword args."""
    _ops(ctx)
    from porterchain_api.batch_engine import scenarios
    if name not in _SCENARIOS:
        raise HTTPException(status_code=404, detail="unknown_scenario")
    try:
        return {"scenario": name, "result": getattr(scenarios, name)(**body)}
    except (TypeError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@admin_router.get("/{batch_id}")
def admin_get(batch_id: str, ctx: Annotated[AdminContext, Depends(get_admin_context)], db: Session = Depends(get_db)):
    _ops(ctx)
    b = db.get(DeliveryBatch, batch_id)
    if not b:
        raise HTTPException(status_code=404, detail="batch_not_found")
    return svc.batch_out(db, b)


class AssignBody(BaseModel):
    driver_id: str = Field(min_length=1, max_length=36)


@admin_router.post("/routes/{route_id}/assign")
def assign(route_id: str, body: AssignBody, ctx: Annotated[AdminContext, Depends(get_admin_context)],
           db: Session = Depends(get_db)):
    _ops(ctx)
    try:
        with db_transaction(db):
            r = svc.assign(db, route_id, body.driver_id)
            return {"route_id": r.id, "driver_id": r.driver_id}
    except (ValueError, LookupError) as exc:
        raise _http(exc) from exc


@admin_router.get("/parcels/{parcel_id}/custody")
def custody(parcel_id: str, ctx: Annotated[AdminContext, Depends(get_admin_context)], db: Session = Depends(get_db)):
    _ops(ctx)
    return {"events": svc.custody_chain(db, parcel_id)}


class DependBody(BaseModel):
    upstream_route_id: str
    handover_point: dict


@admin_router.post("/routes/{route_id}/depends-on")
def depends_on(route_id: str, body: DependBody, ctx: Annotated[AdminContext, Depends(get_admin_context)],
               db: Session = Depends(get_db)):
    """B's parcels come via A (meeting point or depot): B stays hidden until A confirms pickup."""
    _ops(ctx)
    try:
        with db_transaction(db):
            b = svc.make_dependent(db, route_id, body.upstream_route_id, body.handover_point)
            return {"route_id": b.id, "status": b.status, "depends_on_route_id": b.depends_on_route_id}
    except (ValueError, LookupError) as exc:
        raise _http(exc) from exc


class OptimiseBody(BaseModel):
    vehicles: list[dict] = Field(min_length=1, max_length=200)
    jobs: list[dict] = Field(min_length=1, max_length=2000)
    event: dict | None = None


@admin_router.post("/optimise")
def optimise(body: OptimiseBody, ctx: Annotated[AdminContext, Depends(get_admin_context)]):
    """Stateless multi-vehicle VRP (VROOM if VROOM_URL is set, else built-in). Shows saved time vs naive."""
    _ops(ctx)
    from porterchain_api.batch_engine import vrp
    from porterchain_api.config import get_settings
    try:
        vs = [vrp.Vehicle(**{**v, "start": tuple(v["start"]), **({"end": tuple(v["end"])} if v.get("end") else {})})
              for v in body.vehicles]
        js = [vrp.Job(**{**j, "loc": tuple(j["loc"]), **({"tw": tuple(j["tw"])} if j.get("tw") else {})})
              for j in body.jobs]
    except (TypeError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=f"bad_problem:{exc}") from exc
    if body.event:
        ev = dict(body.event)
        if ev.get("type") == "new_order" and isinstance(ev.get("job"), dict):
            j = ev["job"]
            ev["job"] = vrp.Job(**{**j, "loc": tuple(j["loc"]), **({"tw": tuple(j["tw"])} if j.get("tw") else {})})
        try:
            return vrp.reoptimise(vs, js, ev)
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    st = get_settings()
    return vrp.solve_best(vs, js, vroom_url=getattr(st, "vroom_url", "") or "",
                          valhalla_url=getattr(st, "valhalla_url", "") or "")
