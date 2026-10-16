"""Scan-anytime label lookup + scan history (driver app camera; portal manual fallback).

Security: a code only resolves a parcel on an ACTIVE order owned by this driver.
Anything else (forged, unknown, someone else's, finished) returns the same 404
``not_yours`` with no data. Rate limited and audited with driver, time and GPS.
"""

from __future__ import annotations

from typing import Any

from fastapi import Body

from porterchain_api.driver_engine import scan_audit, scan_service
from porterchain_api.routers.driver._deps import (
    Annotated,
    Depends,
    DriverContext,
    HTTPException,
    Session,
    get_db,
    get_driver_context,
    require_approved_driver,
    router,
)


@router.post("/scan/lookup")
def scan_lookup(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    body: dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
):
    require_approved_driver(ctx)
    scan_audit.enforce_scan_rate(ctx.driver.id)
    try:
        return scan_service.lookup(db, ctx.driver.id, body)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail={"code": "not_yours"}) from exc


@router.get("/scan/history")
def scan_history(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    limit: int = 50,
    db: Session = Depends(get_db),
):
    require_approved_driver(ctx)
    return {"items": scan_audit.scan_history(db, ctx.driver.id, limit)}
