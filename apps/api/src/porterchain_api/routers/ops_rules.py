"""Admin: locations + access notes, driver equipment, exception codes, mid-route change decision.
Merchant + customer: concealed damage claims."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext, AdminRole
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.auth.merchant import get_merchant_context
from porterchain_api.db import db_transaction, get_db
from porterchain_api.ops_rules import codes, rules
from porterchain_api.ops_rules import service as OS

admin_router = APIRouter(prefix="/v1/admin/ops-rules", tags=["admin-ops-rules"])
merchant_router = APIRouter(prefix="/v1/merchant/claims", tags=["merchant-claims"])
_OPS = (AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.DISPATCHER, AdminRole.FLEET_MANAGER,
        AdminRole.SUPPORT, AdminRole.SUPPORT_LEAD)


def _ops(ctx: AdminContext) -> None:
    if ctx.role not in _OPS:
        raise HTTPException(status_code=403, detail="ops_role_required")


def _http(exc: Exception) -> HTTPException:
    code = 404 if isinstance(exc, LookupError) else 403 if isinstance(exc, PermissionError) else 422
    return HTTPException(status_code=code, detail=str(exc))


@admin_router.get("/exception-codes")
def exception_codes(ctx: AdminContext = Depends(get_admin_context)):
    _ops(ctx)
    return {"codes": [c.__dict__ for c in codes.CODES], "aliases": codes.ALIASES}


class LocationBody(BaseModel):
    address: str = Field(min_length=3, max_length=500)
    kind: str = "building"
    lat: float | None = None
    lng: float | None = None
    access_notes: str | None = Field(None, max_length=2000)
    hours: dict | None = None
    units: dict[str, str] | None = None  # unit -> access notes


@admin_router.post("/locations")
def upsert_location(body: LocationBody, ctx: AdminContext = Depends(get_admin_context), db: Session = Depends(get_db)):
    _ops(ctx)
    with db_transaction(db):
        loc = OS.upsert_location(db, body.address, lat=body.lat, lng=body.lng, kind=body.kind,
                                 access_notes=body.access_notes, hours=body.hours)
        for unit, notes in (body.units or {}).items():
            OS.set_unit_notes(db, loc.id, unit, notes)
        return {"id": loc.id, "building_key": loc.building_key, **OS.access_for(db, loc.building_key)}


class EquipmentBody(BaseModel):
    tags: list[str] = Field(max_length=20)


@admin_router.put("/drivers/{driver_id}/equipment")
def set_equipment(driver_id: str, body: EquipmentBody, ctx: AdminContext = Depends(get_admin_context),
                  db: Session = Depends(get_db)):
    _ops(ctx)
    try:
        with db_transaction(db):
            return {"driver_id": driver_id, "tags": OS.set_equipment(db, driver_id, body.tags)}
    except ValueError as exc:
        raise _http(exc) from exc


class MatchBody(BaseModel):
    handling: list[str] = Field(default_factory=list)
    extra: list[str] = Field(default_factory=list)
    drivers: list[dict[str, Any]] = Field(max_length=500)


@admin_router.post("/equipment-match")
def equipment_match(body: MatchBody, ctx: AdminContext = Depends(get_admin_context), db: Session = Depends(get_db)):
    """Dispatch filter: drivers (ids) whose stored equipment covers the job's needs."""
    _ops(ctx)
    from porterchain_api.ops_rules.models import DriverEquipment
    try:
        req = rules.required_equipment(body.handling, body.extra)
    except ValueError as exc:
        raise _http(exc) from exc
    ds = [{"id": d["id"], "equipment": (db.get(DriverEquipment, d["id"]).tags if db.get(DriverEquipment, d["id"]) else [])}
          for d in body.drivers]
    return {"required": req, "eligible": rules.eligible_drivers(req, ds)}


class ChangeBody(BaseModel):
    new_lat: float | None = None
    new_lng: float | None = None
    time_change: bool = False


@admin_router.post("/orders/{order_id}/change-check")
def change_check(order_id: str, body: ChangeBody, ctx: AdminContext = Depends(get_admin_context),
                 db: Session = Depends(get_db)):
    """SC-017: may this order's address/time still change, and how (live re-route, fee/next day)?"""
    _ops(ctx)
    from porterchain_api.booking_models import Order
    o = db.get(Order, order_id)
    if not o:
        raise HTTPException(status_code=404, detail="order_not_found")
    d = o.dropoff or {}
    old = (d["lat"], d["lng"]) if d.get("lat") is not None and d.get("lng") is not None else None
    new = (body.new_lat, body.new_lng) if body.new_lat is not None and body.new_lng is not None else None
    return rules.change_decision(o.state, old, new, time_change=body.time_change)


class DamageBody(BaseModel):
    photos: list[str] = Field(min_length=1, max_length=20)
    note: str = Field(min_length=3, max_length=4000)


@merchant_router.post("/orders/{order_id}/concealed-damage")
def merchant_concealed(order_id: str, body: DamageBody, ctx=Depends(get_merchant_context),
                       db: Session = Depends(get_db)):
    from porterchain_api.booking_models import Order
    o = db.get(Order, order_id)
    if not o or str(o.merchant_id or "") != str(ctx.merchant.id):
        raise HTTPException(status_code=404, detail="order_not_found")
    try:
        with db_transaction(db):
            c = OS.concealed_damage_claim(db, o, reporter="merchant", photos=body.photos, note=body.note)
            return {"id": c.id, "status": c.status, "evidence": c.evidence}
    except ValueError as exc:
        raise _http(exc) from exc


@admin_router.get("/edi/batches/{batch_id}/{kind}")
def edi_export(batch_id: str, kind: str, receiver: str = "PARTNER", ctx: AdminContext = Depends(get_admin_context),
               db: Session = Depends(get_db)):
    """Doc 84 Q7 (decided): X12 214 / 856 style export for an enterprise shipper's batch. Download only."""
    _ops(ctx)
    from porterchain_api.ops_rules.edi_service import export_batch
    try:
        return export_batch(db, batch_id, kind, receiver)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@admin_router.get("/media/{key:path}")
def media_get(key: str, ctx: AdminContext = Depends(get_admin_context)):
    """Ops view of a stored proof photo or signature, streamed through the API."""
    _ops(ctx)
    from porterchain_api.media_store.view import fetch
    try:
        return fetch(key)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="media_not_found") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
