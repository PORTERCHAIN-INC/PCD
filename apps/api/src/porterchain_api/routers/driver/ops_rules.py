"""Driver: safety stops, unlabelled parcel, end-of-shift check, equipment check, building access notes."""
from pydantic import BaseModel, Field

from porterchain_api.db import db_transaction
from porterchain_api.ops_rules import models as _models  # noqa: F401
from porterchain_api.ops_rules import rules
from porterchain_api.ops_rules import service as OS
from porterchain_api.media_store.service import require_own_keys
from porterchain_api.routers.driver._deps import (
    Annotated, Depends, DriverContext, HTTPException, Session, get_db, get_driver_context, router,
)

Ctx = Annotated[DriverContext, Depends(get_driver_context)]


def _http(exc: Exception) -> HTTPException:
    code = 404 if isinstance(exc, LookupError) else 403 if isinstance(exc, PermissionError) else 422
    return HTTPException(status_code=code, detail=str(exc))


class SafetyBody(BaseModel):
    code: str
    order_id: str | None = None
    route_id: str | None = None
    address: str | None = None
    parcels: list[str] = Field(default_factory=list, max_length=500)
    note: str | None = Field(None, max_length=2000)
    photo_keys: list[str] = Field(default_factory=list, max_length=20)
    police_report_no: str | None = Field(None, max_length=64)
    signature_key: str | None = Field(None, max_length=256)


@router.post("/safety-stop")
def safety_stop(body: SafetyBody, ctx: Ctx, db: Session = Depends(get_db)):
    try:
        require_own_keys(body.model_dump(), str(ctx.driver.id))
        with db_transaction(db):
            return OS.safety_stop(db, body.code, str(ctx.driver.id), **body.model_dump(exclude={"code"}))
    except (ValueError, LookupError, PermissionError) as exc:
        raise _http(exc) from exc


class UnlabelledBody(BaseModel):
    photo_keys: list[str] = Field(min_length=1, max_length=10)
    parcel_id: str | None = None


@router.post("/batches/routes/{route_id}/unlabelled")
def unlabelled(route_id: str, body: UnlabelledBody, ctx: Ctx, db: Session = Depends(get_db)):
    try:
        require_own_keys(body.model_dump(), str(ctx.driver.id))
        with db_transaction(db):
            return OS.unlabelled_parcel(db, route_id, str(ctx.driver.id), photo_keys=body.photo_keys,
                                        parcel_id=body.parcel_id)
    except (ValueError, LookupError, PermissionError) as exc:
        raise _http(exc) from exc


@router.get("/end-of-shift")
def end_of_shift(ctx: Ctx, db: Session = Depends(get_db)):
    return OS.end_shift_check(db, str(ctx.driver.id))


@router.get("/equipment-check")
def equipment_check(ctx: Ctx, handling: str = "", extra: str = "", db: Session = Depends(get_db)):
    try:
        req = rules.required_equipment([h for h in handling.split(",") if h], [e for e in extra.split(",") if e])
    except ValueError as exc:
        raise _http(exc) from exc
    return {"required": req, **OS.equipment_check(db, str(ctx.driver.id), req)}


@router.get("/locations/access")
def access(building_key: str, ctx: Ctx, unit: str | None = None, db: Session = Depends(get_db)):
    return OS.access_for(db, building_key, unit)


@router.get("/ui-lock")
def ui_lock(speed_kmh: float, ctx: Ctx):
    return {"locked": rules.ui_locked(speed_kmh), "limit_kmh": rules.UI_LOCK_KMH}
