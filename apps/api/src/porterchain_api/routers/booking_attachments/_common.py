"""Shared helpers for booking-attachment routes."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import Depends, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.auth.driver import get_driver_context
from porterchain_api.auth.merchant import get_merchant_context
from porterchain_api.booking_attachments import service as svc
from porterchain_api.db import db_transaction
from porterchain_api.driver_engine.rbac import DriverContext
from porterchain_api.merchant_engine.rbac import MerchantContext

MCtx = Annotated[MerchantContext, Depends(get_merchant_context)]
DCtx = Annotated[DriverContext, Depends(get_driver_context)]
ACtx = Annotated[AdminContext, Depends(get_admin_context)]


class AttachmentPatch(BaseModel):
    kind: str | None = None
    stop: str | None = None
    required_at_stop: bool | None = None
    note: str | None = None


def call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except svc.AttachmentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def tx(db, fn, *args, **kwargs):
    """Run a mutating service call as one unit of work."""
    with db_transaction(db):
        return call(fn, *args, **kwargs)


def file_response(att, data: bytes, ctype: str | None = None) -> Response:
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


async def read(file: UploadFile) -> bytes:
    return await file.read(svc.MAX_BYTES + 1)


def parse_addr(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        val = json.loads(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="location_address_invalid") from exc
    return val if isinstance(val, dict) else None


def owner_upload(
    db,
    owner_type,
    owner_id,
    actor_id,
    order_id,
    data,
    filename,
    kind,
    stop,
    required,
    note,
    save_for_location,
    location_address=None,
):
    return tx(
        db,
        svc.upload,
        db,
        owner_type=owner_type,
        owner_id=owner_id,
        actor_id=actor_id,
        order_id=order_id,
        data=data,
        filename=filename or "document",
        kind=kind or None,
        stop=stop or None,
        required_at_stop=required,
        note=note,
        save_for_location=save_for_location,
        location_address=parse_addr(location_address),
    )


def suggestion(data: bytes, filename: str) -> dict:
    ctype = call(svc.validate_file, data)
    kind = svc.suggest_kind(filename or "", data)
    return {
        "kind": kind,
        "kind_label": svc.KINDS[kind],
        "stop": svc.DEFAULT_STOP[kind],
        "content_type": ctype,
    }
