"""Pickup documents (view) + instructions for admin / merchant / customer / partner (via ops).

Subjects: an order (`/orders/{id}`) or a bulk batch (`/batches/{id}`; parcel = batch parcel id).
Partners have no portal login: ops records partner instructions with `as_partner_id` (author_role=partner).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext, AdminRole
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.auth.bearer import get_identity_claims
from porterchain_api.auth.claims import IdentityClaims
from porterchain_api.auth.merchant import get_merchant_context
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import db_transaction, get_db
from porterchain_api.job_docs import service as JD

admin_router = APIRouter(prefix="/v1/admin/jobs", tags=["admin-job-docs"])
merchant_router = APIRouter(prefix="/v1/merchant/jobs", tags=["merchant-job-docs"])
customer_router = APIRouter(prefix="/v1/customer/jobs", tags=["customer-job-docs"])
_OPS = (AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.DISPATCHER, AdminRole.FLEET_MANAGER,
        AdminRole.SUPPORT, AdminRole.SUPPORT_LEAD)


class InstructionBody(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    photo_key: str | None = None
    priority: str = "normal"
    visibility: list[str] | None = None
    steps: list[str] | None = None
    business: bool = False
    parcel_id: str | None = None
    as_partner_id: str | None = None


class EditBody(BaseModel):
    text: str | None = None
    photo_key: str | None = None
    priority: str | None = None
    visibility: list[str] | None = None
    steps: list[str] | None = None
    business: bool | None = None
    delete: bool = False


def _http(exc: Exception) -> HTTPException:
    code = 404 if isinstance(exc, LookupError) else 403 if isinstance(exc, PermissionError) else 422
    return HTTPException(status_code=code, detail=str(exc))


def _subject(kind: str, sid: str) -> dict[str, str]:
    if kind == "orders":
        return {"order_id": sid}
    if kind == "batches":
        return {"route_id": sid}
    raise HTTPException(status_code=404, detail="bad_subject")


def _merchant_owns(db: Session, merchant_id: str, kind: str, sid: str) -> None:
    from porterchain_api.batch_engine.models import DeliveryBatch
    from porterchain_api.booking_models import Order
    row = db.get(Order, sid) if kind == "orders" else db.get(DeliveryBatch, sid)
    if not row or str(getattr(row, "merchant_id", "")) != merchant_id:
        raise HTTPException(status_code=404, detail="job_not_found")


def _docs(db: Session, kind: str, sid: str) -> dict[str, Any]:
    if kind == "orders":
        return {"documents": JD.documents_out(db, order_id=sid)}
    route_ids = JD.batch_route_ids(db, sid)
    return {"documents": [{**d, "route_id": rid} for rid in route_ids for d in JD.documents_out(db, route_id=rid)]}


def _body(b: BaseModel) -> dict[str, Any]:
    return {k: v for k, v in b.model_dump().items() if v is not None and k not in ("as_partner_id", "delete")}


# ---- admin / ops (also partner-on-behalf)
def _ops(ctx: AdminContext) -> None:
    if ctx.role not in _OPS:
        raise HTTPException(status_code=403, detail="ops_role_required")


@admin_router.get("/{kind}/{sid}/pickup-docs")
def admin_docs(kind: str, sid: str, ctx: AdminContext = Depends(get_admin_context), db: Session = Depends(get_db)):
    _ops(ctx)
    _subject(kind, sid)
    return _docs(db, kind, sid)


@admin_router.get("/{kind}/{sid}/instructions")
def admin_list(kind: str, sid: str, ctx: AdminContext = Depends(get_admin_context), db: Session = Depends(get_db)):
    _ops(ctx)
    return {"items": JD.for_viewer(db, "admin", **_subject(kind, sid))}


@admin_router.post("/{kind}/{sid}/instructions")
def admin_add(kind: str, sid: str, body: InstructionBody, ctx: AdminContext = Depends(get_admin_context),
              db: Session = Depends(get_db)):
    _ops(ctx)
    role, author = ("partner", body.as_partner_id) if body.as_partner_id else ("admin", ctx.user.auth_subject)
    try:
        with db_transaction(db):
            i = JD.add_instruction(db, role, author, _body(body), **_subject(kind, sid))
            return {"id": i.id, "version": i.version}
    except (ValueError, PermissionError) as exc:
        raise _http(exc) from exc


@admin_router.patch("/instructions/{iid}")
def admin_edit(iid: str, body: EditBody, ctx: AdminContext = Depends(get_admin_context), db: Session = Depends(get_db)):
    _ops(ctx)
    try:
        with db_transaction(db):
            i = JD.edit_instruction(db, iid, "admin", ctx.user.auth_subject, _body(body), delete=body.delete)
            return {"id": i.id, "version": i.version, "deleted": i.deleted}
    except (ValueError, PermissionError, LookupError) as exc:
        raise _http(exc) from exc


@admin_router.get("/instructions/{iid}/history")
def admin_history(iid: str, ctx: AdminContext = Depends(get_admin_context), db: Session = Depends(get_db)):
    _ops(ctx)
    return {"items": JD.history(db, iid)}


# ---- merchant
@merchant_router.get("/{kind}/{sid}/pickup-docs")
def merchant_docs(kind: str, sid: str, ctx=Depends(get_merchant_context), db: Session = Depends(get_db)):
    _merchant_owns(db, str(ctx.merchant.id), kind, sid)
    return _docs(db, kind, sid)


@merchant_router.get("/{kind}/{sid}/instructions")
def merchant_list(kind: str, sid: str, ctx=Depends(get_merchant_context), db: Session = Depends(get_db)):
    _merchant_owns(db, str(ctx.merchant.id), kind, sid)
    return {"items": JD.for_viewer(db, "merchant", **_subject(kind, sid))}


@merchant_router.post("/{kind}/{sid}/instructions")
def merchant_add(kind: str, sid: str, body: InstructionBody, ctx=Depends(get_merchant_context),
                 db: Session = Depends(get_db)):
    _merchant_owns(db, str(ctx.merchant.id), kind, sid)
    try:
        with db_transaction(db):
            i = JD.add_instruction(db, "merchant", str(ctx.merchant.id), _body(body), **_subject(kind, sid))
            return {"id": i.id, "version": i.version}
    except (ValueError, PermissionError) as exc:
        raise _http(exc) from exc


@merchant_router.patch("/instructions/{iid}")
def merchant_edit(iid: str, body: EditBody, ctx=Depends(get_merchant_context), db: Session = Depends(get_db)):
    try:
        with db_transaction(db):
            i = JD.edit_instruction(db, iid, "merchant", str(ctx.merchant.id), _body(body), delete=body.delete)
            return {"id": i.id, "version": i.version, "deleted": i.deleted}
    except (ValueError, PermissionError, LookupError) as exc:
        raise _http(exc) from exc


# ---- customer (own delivery only)
def _customer(db: Session, claims: IdentityClaims, settings: Settings):
    from porterchain_api.auth.customer import require_customer
    return require_customer(db, claims, settings)


def _own_order(db: Session, customer_id: str, order_id: str):
    from porterchain_api.booking_models import Order
    o = db.get(Order, order_id)
    if not o or str(o.customer_id or "") != str(customer_id):
        raise HTTPException(status_code=404, detail="order_not_found")
    return JD.order_package_ids(db, order_id)


@customer_router.get("/orders/{oid}/instructions")
def customer_list(oid: str, db: Session = Depends(get_db), settings: Settings = Depends(get_settings),
                  claims: IdentityClaims = Depends(get_identity_claims)):
    c = _customer(db, claims, settings)
    _own_order(db, c.id, oid)
    return {"items": JD.for_viewer(db, "customer", order_id=oid)}


@customer_router.post("/orders/{oid}/instructions")
def customer_add(oid: str, body: InstructionBody, db: Session = Depends(get_db),
                 settings: Settings = Depends(get_settings), claims: IdentityClaims = Depends(get_identity_claims)):
    c = _customer(db, claims, settings)
    own = _own_order(db, c.id, oid)
    data = _body(body)
    data.setdefault("steps", ["delivery"])
    data.setdefault("visibility", ["driver", "admin", "customer"])
    try:
        with db_transaction(db):
            i = JD.add_instruction(db, "customer", str(c.id), data, order_id=oid, own_parcels=own)
            return {"id": i.id, "version": i.version}
    except (ValueError, PermissionError) as exc:
        raise _http(exc) from exc


@customer_router.patch("/instructions/{iid}")
def customer_edit(iid: str, body: EditBody, db: Session = Depends(get_db), settings: Settings = Depends(get_settings),
                  claims: IdentityClaims = Depends(get_identity_claims)):
    c = _customer(db, claims, settings)
    try:
        with db_transaction(db):
            i = JD.edit_instruction(db, iid, "customer", str(c.id), _body(body), delete=body.delete)
            return {"id": i.id, "version": i.version, "deleted": i.deleted}
    except (ValueError, PermissionError, LookupError) as exc:
        raise _http(exc) from exc
