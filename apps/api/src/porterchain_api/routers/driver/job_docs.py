"""Driver: pickup document checklist (capture/missing) + step instructions & must-read acks.
Works for single orders (/jobs/{order_id}) and bulk batch routes (/batches/routes/{route_id})."""
from typing import Any

from pydantic import BaseModel

from porterchain_api.db import db_transaction
from porterchain_api.job_docs import models as _models  # noqa: F401
from porterchain_api.job_docs import service as JD
from porterchain_api.media_store.service import require_own_keys
from porterchain_api.routers.driver._deps import (
    Annotated, Depends, DriverContext, HTTPException, Session, get_db, get_driver_context, router,
)

Ctx = Annotated[DriverContext, Depends(get_driver_context)]


class CaptureBody(BaseModel):
    media_key: str | None = None
    scan_code: str | None = None
    seal_no: str | None = None
    shipper_name: str | None = None
    shipper_signature_key: str | None = None
    note: str | None = None


class MissingBody(BaseModel):
    reason: str


def _http(exc: Exception) -> HTTPException:
    from porterchain_api.batch_engine.service import LegLocked
    if isinstance(exc, LegLocked):
        return HTTPException(status_code=423, detail="leg_locked")
    code = 404 if isinstance(exc, LookupError) else 403 if isinstance(exc, PermissionError) else 409
    return HTTPException(status_code=code, detail=str(exc))


def _subject(db: Session, ctx: DriverContext, kind: str, sid: str) -> tuple[list[str], dict[str, str], dict[str, str]]:
    """-> (required docs, docs subject, instructions subject)."""
    did = str(ctx.driver.id)
    if kind == "jobs":
        from porterchain_api.booking_models import Order
        o = db.get(Order, sid)
        if not o or str(o.assigned_driver_id or "") != did:
            raise HTTPException(status_code=404, detail="job_not_found")
        return JD.required_for_order(db, o), {"order_id": sid}, {"order_id": sid}
    if kind == "routes":
        from porterchain_api.batch_engine import service as B
        try:
            r = B._route(db, sid, did)
        except Exception as exc:  # noqa: BLE001
            raise _http(exc) from exc
        return B.route_docs(db, r), {"route_id": r.id}, {"route_id": r.batch_id}
    raise HTTPException(status_code=404, detail="bad_subject")


@router.get("/doc-checklist/{kind}/{sid}")
def checklist(kind: str, sid: str, ctx: Ctx, db: Session = Depends(get_db), phase: str = "at_pickup",
              lang: str = "en") -> dict[str, Any]:
    req, ds, _ = _subject(db, ctx, kind, sid)
    return JD.checklist(db, req, phase=phase, lang=lang, **ds)


@router.post("/doc-checklist/{kind}/{sid}/{doc_type}")
def capture(kind: str, sid: str, doc_type: str, body: CaptureBody, ctx: Ctx, db: Session = Depends(get_db)):
    req, ds, _ = _subject(db, ctx, kind, sid)
    try:
        require_own_keys(body.model_dump(), str(ctx.driver.id))
        with db_transaction(db):
            d = JD.capture(db, req, doc_type, body.model_dump(), str(ctx.driver.id), **ds)
            return {"id": d.id, **JD.checklist(db, req, **ds)}
    except (ValueError, PermissionError) as exc:
        raise _http(exc) from exc


@router.post("/doc-checklist/{kind}/{sid}/{doc_type}/missing")
def missing(kind: str, sid: str, doc_type: str, body: MissingBody, ctx: Ctx, db: Session = Depends(get_db)):
    req, ds, _ = _subject(db, ctx, kind, sid)
    try:
        with db_transaction(db):
            out = JD.report_missing(db, req, doc_type, body.reason, str(ctx.driver.id), **ds)
            return {**out, **JD.checklist(db, req, **ds)}
    except (ValueError, PermissionError) as exc:
        raise _http(exc) from exc


@router.get("/instructions/{kind}/{sid}")
def instructions(kind: str, sid: str, ctx: Ctx, step: str, parcel_id: str | None = None,
                 db: Session = Depends(get_db)) -> dict[str, Any]:
    _, _, isub = _subject(db, ctx, kind, sid)
    try:
        return JD.driver_step(db, str(ctx.driver.id), step, parcel_id=parcel_id, **isub)
    except ValueError as exc:
        raise _http(exc) from exc


@router.post("/instructions/{iid}/ack")
def ack(iid: str, ctx: Ctx, db: Session = Depends(get_db)):
    try:
        with db_transaction(db):
            JD.acknowledge(db, iid, str(ctx.driver.id))
            return {"ok": True}
    except LookupError as exc:
        raise _http(exc) from exc
