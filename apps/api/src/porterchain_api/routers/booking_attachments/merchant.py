"""Merchant: attach documents to own bookings."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from porterchain_api.booking_attachments import service as svc
from porterchain_api.db import get_db
from porterchain_api.merchant_engine.rbac import require_module
from porterchain_api.routers.booking_attachments._common import (
    AttachmentPatch,
    MCtx,
    call,
    file_response,
    owner_upload,
    read,
    suggestion,
    tx,
)

router = APIRouter(prefix="/v1/merchant", tags=["booking-attachments"])


@router.post("/attachments/suggest")
async def merchant_suggest(ctx: MCtx, file: UploadFile = File(...)) -> dict:
    data = await read(file)
    return await run_in_threadpool(suggestion, data, file.filename or "")


@router.get("/orders/{order_id}/attachments")
def merchant_list(order_id: str, ctx: MCtx, db: Session = Depends(get_db)):
    require_module(ctx, "orders")
    return tx(db, svc.list_for_owner, db, "merchant", ctx.merchant.id, order_id)


@router.post("/orders/{order_id}/attachments", status_code=201)
async def merchant_upload(
    order_id: str,
    ctx: MCtx,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    kind: str | None = Form(None),
    stop: str | None = Form(None),
    required_at_stop: bool = Form(True),
    note: str | None = Form(None),
    save_for_location: bool = Form(False),
):
    require_module(ctx, "orders_write")
    data = await read(file)
    return await run_in_threadpool(
        owner_upload,
        db,
        "merchant",
        ctx.merchant.id,
        ctx.user.id,
        order_id,
        data,
        file.filename,
        kind,
        stop,
        required_at_stop,
        note,
        save_for_location,
    )


@router.get("/attachments/locations")
def merchant_location_templates(ctx: MCtx, db: Session = Depends(get_db)):
    require_module(ctx, "orders")
    return {"items": svc.list_location_templates(db, "merchant", ctx.merchant.id)}


@router.post("/attachments/locations", status_code=201)
async def merchant_location_upload(
    ctx: MCtx,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    location_address: str = Form(...),
    kind: str | None = Form(None),
    stop: str = Form("pickup"),
    required_at_stop: bool = Form(True),
    note: str | None = Form(None),
):
    require_module(ctx, "orders_write")
    data = await read(file)
    return await run_in_threadpool(
        owner_upload,
        db,
        "merchant",
        ctx.merchant.id,
        ctx.user.id,
        None,
        data,
        file.filename,
        kind,
        stop,
        required_at_stop,
        note,
        True,
        location_address,
    )


@router.patch("/attachments/{attachment_id}")
def merchant_patch(
    attachment_id: str, body: AttachmentPatch, ctx: MCtx, db: Session = Depends(get_db)
):
    require_module(ctx, "orders_write")
    return tx(
        db,
        svc.update,
        db,
        owner_type="merchant",
        owner_id=ctx.merchant.id,
        actor_id=ctx.user.id,
        attachment_id=attachment_id,
        **body.model_dump(),
    )


@router.delete("/attachments/{attachment_id}", status_code=204)
def merchant_delete(
    attachment_id: str, ctx: MCtx, db: Session = Depends(get_db)
) -> Response:
    require_module(ctx, "orders_write")
    tx(
        db,
        svc.delete,
        db,
        owner_type="merchant",
        owner_id=ctx.merchant.id,
        actor_id=ctx.user.id,
        attachment_id=attachment_id,
    )
    return Response(status_code=204)


@router.get("/attachments/{attachment_id}/file")
def merchant_file(
    attachment_id: str, ctx: MCtx, db: Session = Depends(get_db)
) -> Response:
    require_module(ctx, "orders")
    att, data = tx(
        db,
        svc.owner_download,
        db,
        owner_type="merchant",
        owner_id=ctx.merchant.id,
        actor_id=ctx.user.id,
        attachment_id=attachment_id,
    )
    return file_response(att, data)


__all__ = ["router", "call"]
