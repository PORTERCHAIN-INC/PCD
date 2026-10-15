"""Customer: attach documents to own bookings (keyed by order id or tracking number)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.clerk import get_clerk_claims
from porterchain_api.auth.customer import require_customer
from porterchain_api.booking_attachments import service as svc
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.routers.booking_attachments._common import (
    AttachmentPatch,
    file_response,
    owner_upload,
    read,
    suggestion,
    tx,
)

router = APIRouter(prefix="/v1/customers/me", tags=["booking-attachments"])


@router.post("/attachments/suggest")
async def customer_suggest(
    file: UploadFile = File(...), claims: ClerkClaims = Depends(get_clerk_claims)
):
    del claims  # signed-in only; nothing is stored
    data = await read(file)
    return await run_in_threadpool(suggestion, data, file.filename or "")


@router.get("/orders/{order_id}/attachments")
def customer_list(
    order_id: str,
    db: Session = Depends(get_db),
    claims: ClerkClaims = Depends(get_clerk_claims),
    settings: Settings = Depends(get_settings),
):
    c = require_customer(db, claims, settings)
    return tx(db, svc.list_for_owner, db, "customer", c.id, order_id)


@router.post("/orders/{order_id}/attachments", status_code=201)
async def customer_upload(
    order_id: str,
    db: Session = Depends(get_db),
    claims: ClerkClaims = Depends(get_clerk_claims),
    settings: Settings = Depends(get_settings),
    file: UploadFile = File(...),
    kind: str | None = Form(None),
    stop: str | None = Form(None),
    required_at_stop: bool = Form(True),
    note: str | None = Form(None),
    save_for_location: bool = Form(False),
):
    data = await read(file)

    def _go():
        c = require_customer(db, claims, settings)
        return owner_upload(
            db,
            "customer",
            c.id,
            c.id,
            order_id,
            data,
            file.filename,
            kind,
            stop,
            required_at_stop,
            note,
            save_for_location,
        )

    return await run_in_threadpool(_go)


@router.patch("/attachments/{attachment_id}")
def customer_patch(
    attachment_id: str,
    body: AttachmentPatch,
    db: Session = Depends(get_db),
    claims: ClerkClaims = Depends(get_clerk_claims),
    settings: Settings = Depends(get_settings),
):
    c = require_customer(db, claims, settings)
    return tx(
        db,
        svc.update,
        db,
        owner_type="customer",
        owner_id=c.id,
        actor_id=c.id,
        attachment_id=attachment_id,
        **body.model_dump(),
    )


@router.delete("/attachments/{attachment_id}", status_code=204)
def customer_delete(
    attachment_id: str,
    db: Session = Depends(get_db),
    claims: ClerkClaims = Depends(get_clerk_claims),
    settings: Settings = Depends(get_settings),
):
    c = require_customer(db, claims, settings)
    tx(
        db,
        svc.delete,
        db,
        owner_type="customer",
        owner_id=c.id,
        actor_id=c.id,
        attachment_id=attachment_id,
    )
    return Response(status_code=204)


@router.get("/attachments/{attachment_id}/file")
def customer_file(
    attachment_id: str,
    db: Session = Depends(get_db),
    claims: ClerkClaims = Depends(get_clerk_claims),
    settings: Settings = Depends(get_settings),
):
    c = require_customer(db, claims, settings)
    att, data = tx(
        db,
        svc.owner_download,
        db,
        owner_type="customer",
        owner_id=c.id,
        actor_id=c.id,
        attachment_id=attachment_id,
    )
    return file_response(att, data)
