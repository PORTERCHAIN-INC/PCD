"""Booking attachments — one feature, four audiences (merchant, customer, driver, staff)."""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_engine.rbac import require_module as admin_require_module
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.clerk import get_clerk_claims
from porterchain_api.auth.customer import require_customer
from porterchain_api.auth.driver import get_driver_context
from porterchain_api.auth.merchant import get_merchant_context
from porterchain_api.booking_attachments import service as svc
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.driver_engine.rbac import DriverContext
from porterchain_api.merchant_engine.rbac import MerchantContext, require_module

router = APIRouter(tags=["booking-attachments"])
MCtx = Annotated[MerchantContext, Depends(get_merchant_context)]
DCtx = Annotated[DriverContext, Depends(get_driver_context)]
ACtx = Annotated[AdminContext, Depends(get_admin_context)]


class AttachmentPatch(BaseModel):
    kind: str | None = None
    stop: str | None = None
    required_at_stop: bool | None = None
    note: str | None = None


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except svc.AttachmentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _file(att, data: bytes, ctype: str | None = None) -> Response:
    return Response(
        content=data,
        media_type=ctype or att.content_type,
        headers={
            "Content-Disposition": f'inline; filename="{att.filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'",
        },
    )


async def _read(file: UploadFile) -> bytes:
    return await file.read(svc.MAX_BYTES + 1)


def _addr(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        val = json.loads(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="location_address_invalid") from exc
    return val if isinstance(val, dict) else None


# ── shared owner handlers ────────────────────────────────────────────────

def _owner_upload(db, owner_type, owner_id, actor_id, order_id, data, file, kind, stop, required_at_stop,
                  note, save_for_location, location_address):
    out = _call(svc.upload, db, owner_type=owner_type, owner_id=owner_id, actor_id=actor_id, order_id=order_id,
                data=data, filename=file.filename or "document", kind=kind or None, stop=stop or None,
                required_at_stop=required_at_stop, note=note, save_for_location=save_for_location,
                location_address=_addr(location_address))
    db.commit()
    return out


# ── merchant ─────────────────────────────────────────────────────────────

@router.post("/v1/merchant/attachments/suggest")
async def merchant_suggest(ctx: MCtx, file: UploadFile = File(...)) -> dict[str, Any]:
    data = await _read(file)
    ctype = await run_in_threadpool(_call, svc.validate_file, data)
    kind = svc.suggest_kind(file.filename or "", data)
    return {"kind": kind, "kind_label": svc.KINDS[kind], "stop": svc.DEFAULT_STOP[kind], "content_type": ctype}


@router.get("/v1/merchant/orders/{order_id}/attachments")
def merchant_list(order_id: str, ctx: MCtx, db: Session = Depends(get_db)):
    require_module(ctx, "orders")
    out = _call(svc.list_for_owner, db, "merchant", ctx.merchant.id, order_id)
    db.commit()
    return out


@router.post("/v1/merchant/orders/{order_id}/attachments", status_code=201)
async def merchant_upload(
    order_id: str, ctx: MCtx, db: Session = Depends(get_db), file: UploadFile = File(...),
    kind: str | None = Form(None), stop: str | None = Form(None), required_at_stop: bool = Form(True),
    note: str | None = Form(None), save_for_location: bool = Form(False),
):
    require_module(ctx, "orders_write")
    data = await _read(file)
    return await run_in_threadpool(_owner_upload, db, "merchant", ctx.merchant.id, ctx.user.id, order_id, data,
                                   file, kind, stop, required_at_stop, note, save_for_location, None)


@router.get("/v1/merchant/attachments/locations")
def merchant_location_templates(ctx: MCtx, db: Session = Depends(get_db)):
    require_module(ctx, "orders")
    return {"items": svc.list_location_templates(db, "merchant", ctx.merchant.id)}


@router.post("/v1/merchant/attachments/locations", status_code=201)
async def merchant_location_upload(
    ctx: MCtx, db: Session = Depends(get_db), file: UploadFile = File(...),
    location_address: str = Form(...), kind: str | None = Form(None), stop: str = Form("pickup"),
    required_at_stop: bool = Form(True), note: str | None = Form(None),
):
    require_module(ctx, "orders_write")
    data = await _read(file)
    return await run_in_threadpool(_owner_upload, db, "merchant", ctx.merchant.id, ctx.user.id, None, data,
                                   file, kind, stop, required_at_stop, note, True, location_address)


@router.patch("/v1/merchant/attachments/{attachment_id}")
def merchant_patch(attachment_id: str, body: AttachmentPatch, ctx: MCtx, db: Session = Depends(get_db)):
    require_module(ctx, "orders_write")
    out = _call(svc.update, db, owner_type="merchant", owner_id=ctx.merchant.id, actor_id=ctx.user.id,
                attachment_id=attachment_id, **body.model_dump())
    db.commit()
    return out


@router.delete("/v1/merchant/attachments/{attachment_id}", status_code=204)
def merchant_delete(attachment_id: str, ctx: MCtx, db: Session = Depends(get_db)) -> Response:
    require_module(ctx, "orders_write")
    _call(svc.delete, db, owner_type="merchant", owner_id=ctx.merchant.id, actor_id=ctx.user.id,
          attachment_id=attachment_id)
    db.commit()
    return Response(status_code=204)


@router.get("/v1/merchant/attachments/{attachment_id}/file")
def merchant_file(attachment_id: str, ctx: MCtx, db: Session = Depends(get_db)) -> Response:
    require_module(ctx, "orders")
    att, data = _call(svc.owner_download, db, owner_type="merchant", owner_id=ctx.merchant.id,
                      actor_id=ctx.user.id, attachment_id=attachment_id)
    db.commit()
    return _file(att, data)


# ── customer ─────────────────────────────────────────────────────────────

def _customer(db: Session, claims: ClerkClaims, settings: Settings):
    return require_customer(db, claims, settings)


@router.post("/v1/customers/me/attachments/suggest")
async def customer_suggest(file: UploadFile = File(...), claims: ClerkClaims = Depends(get_clerk_claims)):
    del claims  # signed-in customers only; nothing is stored
    data = await _read(file)
    ctype = await run_in_threadpool(_call, svc.validate_file, data)
    kind = svc.suggest_kind(file.filename or "", data)
    return {"kind": kind, "kind_label": svc.KINDS[kind], "stop": svc.DEFAULT_STOP[kind], "content_type": ctype}


@router.get("/v1/customers/me/orders/{order_id}/attachments")
def customer_list(order_id: str, db: Session = Depends(get_db), claims: ClerkClaims = Depends(get_clerk_claims),
                  settings: Settings = Depends(get_settings)):
    c = _customer(db, claims, settings)
    out = _call(svc.list_for_owner, db, "customer", c.id, order_id)
    db.commit()
    return out


@router.post("/v1/customers/me/orders/{order_id}/attachments", status_code=201)
async def customer_upload(
    order_id: str, db: Session = Depends(get_db), claims: ClerkClaims = Depends(get_clerk_claims),
    settings: Settings = Depends(get_settings), file: UploadFile = File(...), kind: str | None = Form(None),
    stop: str | None = Form(None), required_at_stop: bool = Form(True), note: str | None = Form(None),
    save_for_location: bool = Form(False),
):
    data = await _read(file)

    def _go():
        c = _customer(db, claims, settings)
        return _owner_upload(db, "customer", c.id, c.id, order_id, data, file, kind, stop, required_at_stop,
                             note, save_for_location, None)

    return await run_in_threadpool(_go)


@router.patch("/v1/customers/me/attachments/{attachment_id}")
def customer_patch(attachment_id: str, body: AttachmentPatch, db: Session = Depends(get_db),
                   claims: ClerkClaims = Depends(get_clerk_claims), settings: Settings = Depends(get_settings)):
    c = _customer(db, claims, settings)
    out = _call(svc.update, db, owner_type="customer", owner_id=c.id, actor_id=c.id,
                attachment_id=attachment_id, **body.model_dump())
    db.commit()
    return out


@router.delete("/v1/customers/me/attachments/{attachment_id}", status_code=204)
def customer_delete(attachment_id: str, db: Session = Depends(get_db),
                    claims: ClerkClaims = Depends(get_clerk_claims), settings: Settings = Depends(get_settings)):
    c = _customer(db, claims, settings)
    _call(svc.delete, db, owner_type="customer", owner_id=c.id, actor_id=c.id, attachment_id=attachment_id)
    db.commit()
    return Response(status_code=204)


@router.get("/v1/customers/me/attachments/{attachment_id}/file")
def customer_file(attachment_id: str, db: Session = Depends(get_db),
                  claims: ClerkClaims = Depends(get_clerk_claims), settings: Settings = Depends(get_settings)):
    c = _customer(db, claims, settings)
    att, data = _call(svc.owner_download, db, owner_type="customer", owner_id=c.id, actor_id=c.id,
                      attachment_id=attachment_id)
    db.commit()
    return _file(att, data)


# ── driver ───────────────────────────────────────────────────────────────

@router.get("/driver-api/v1/orders/{order_id}/attachments")
def driver_list(order_id: str, ctx: DCtx, db: Session = Depends(get_db)):
    out = _call(svc.list_for_driver, db, ctx.driver.id, order_id)
    db.commit()
    return out


@router.get("/driver-api/v1/attachments/{attachment_id}/file")
def driver_file(attachment_id: str, ctx: DCtx, db: Session = Depends(get_db)) -> Response:
    att, data = _call(svc.driver_download, db, ctx.driver.id, attachment_id)
    db.commit()
    return _file(att, data)


@router.post("/driver-api/v1/attachments/{attachment_id}/link")
def driver_link(attachment_id: str, ctx: DCtx, db: Session = Depends(get_db),
                settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    token = _call(svc.driver_link, db, ctx.driver.id, attachment_id)
    db.commit()
    base = (getattr(settings, "public_api_url", None) or "").rstrip("/")
    return {"path": f"/v1/attachment-links/{token}", "url": f"{base}/v1/attachment-links/{token}" if base else None,
            "expires_in": int(svc.LINK_TTL.total_seconds())}


@router.get("/v1/attachment-links/{token}")
def redeem_link(token: str, db: Session = Depends(get_db)) -> Response:
    att, data = _call(svc.redeem_link, db, token)
    db.commit()
    return _file(att, data)


@router.post("/driver-api/v1/attachments/{attachment_id}/shown")
async def driver_shown(attachment_id: str, ctx: DCtx, db: Session = Depends(get_db),
                       proof: UploadFile | None = File(None)):
    data = await _read(proof) if proof is not None else None
    def _go():
        out = _call(svc.mark_shown, db, ctx.driver.id, attachment_id, data or None)
        db.commit()
        return out

    return await run_in_threadpool(_go)


# ── staff ────────────────────────────────────────────────────────────────

@router.get("/v1/admin/orders/{order_id}/attachments")
def staff_list(order_id: str, ctx: ACtx, db: Session = Depends(get_db)):
    admin_require_module(ctx, "orders")
    return svc.list_for_staff(db, order_id)


@router.get("/v1/admin/attachments/{attachment_id}/file")
def staff_file(attachment_id: str, ctx: ACtx, db: Session = Depends(get_db), proof: bool = False) -> Response:
    admin_require_module(ctx, "orders")
    att, data, ctype = _call(svc.staff_download, db, str(ctx.user.id), attachment_id, proof=proof)
    db.commit()
    return _file(att, data, ctype)
