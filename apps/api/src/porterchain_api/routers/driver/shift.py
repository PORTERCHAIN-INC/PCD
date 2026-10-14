"""driver routes — shift."""

from porterchain_api.db import db_transaction
from porterchain_api.routers.driver._deps import (
    Annotated,
    Depends,
    DocumentUploadRequest,
    DriverContext,
    HTTPException,
    Session,
    get_db,
    get_driver_context,
    router,
    svc)


@router.get("/vehicle")
def get_vehicle(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return {"vehicle": svc.platform.vehicle.get_active_vehicle(db, ctx.driver.id), "vehicles": svc.platform.vehicle.list_vehicles(db, ctx.driver.id)}


@router.get("/insurance")
def insurance(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return svc.platform.insurance.status(db, ctx.driver)


@router.get("/documents")
def list_documents(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    include_files: bool = True):
    """`include_files=false` drops inline data: URLs (the app lists status/expiry only)."""
    docs = svc.platform.documents
    return {"documents": docs.list_documents(ctx.driver) if include_files else docs.list_documents_lite(ctx.driver)}


@router.post("/documents")
def upload_document(
    body: DocumentUploadRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db)):
    try:
        with db_transaction(db):
            doc = svc.platform.documents.upload_document(
                db,
                ctx.driver,
                doc_type=body.doc_type,
                file_url=body.file_url,
                metadata=body.metadata)
        return doc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/profile/vehicle-photos")
def upload_vehicle_photo(
    body: DocumentUploadRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db)):
    with db_transaction(db):
        photo = svc.platform.documents.upload_vehicle_photo(
            db, ctx.driver, file_url=body.file_url, metadata=body.metadata
        )
    return photo


@router.get("/training")
def training(ctx: Annotated[DriverContext, Depends(get_driver_context)]):
    return {"modules": svc.platform.training.list_modules(ctx.driver)}


@router.post("/training/{module_id}/complete")
def complete_training(
    module_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db)):
    with db_transaction(db):
        result = svc.platform.training.complete_module(db, ctx.driver, module_id)
    return result




# ---------- App settings + privacy request (driver mobile Settings page) ----------
_PRIVACY_KINDS = {"access", "correction", "deletion"}


@router.get("/settings")
def get_app_settings(ctx: Annotated[DriverContext, Depends(get_driver_context)]):
    from porterchain_driver.app_settings import read_settings

    return {"settings": read_settings(ctx.driver)}


@router.put("/settings")
def put_app_settings(
    body: dict,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db)):
    """Merge-update; unknown keys and bad values are dropped. Notification flags gate push by type."""
    from porterchain_driver.app_settings import merge_settings

    raw = body.get("settings") if isinstance(body.get("settings"), dict) else body
    with db_transaction(db):
        merged = merge_settings(db, ctx.driver, raw)
    return {"settings": merged}


@router.post("/privacy/request")
def privacy_request(
    body: dict,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db)):
    """PIPEDA access / correction / deletion request → a tracked privacy ticket (30-day SLA)."""
    kind = str(body.get("kind") or "")
    if kind not in _PRIVACY_KINDS:
        raise HTTPException(status_code=422, detail="invalid_privacy_kind")
    note = str(body.get("note") or "")[:1000] or None
    with db_transaction(db):
        ticket = svc.platform.support.create_ticket(
            db,
            ctx.driver,
            subject=f"Privacy request: {kind}",
            description=note,
            priority="high",
            category="privacy")
    ref = ticket.get("id") if isinstance(ticket, dict) else None
    return {"status": "received", "kind": kind, "reference": ref, "sla_days": 30}
