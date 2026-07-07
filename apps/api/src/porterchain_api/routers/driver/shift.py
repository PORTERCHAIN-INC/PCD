"""driver routes — shift."""

from porterchain_api.routers.driver._deps import *  # noqa: F403

@router.get("/vehicle")
def get_vehicle(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return {"vehicle": svc.platform.vehicle.get_active_vehicle(db, ctx.driver.id), "vehicles": svc.platform.vehicle.list_vehicles(db, ctx.driver.id)}


@router.get("/insurance")
def insurance(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return svc.platform.insurance.status(db, ctx.driver)


@router.get("/documents")
def list_documents(ctx: Annotated[DriverContext, Depends(get_driver_context)]):
    return {"documents": svc.platform.documents.list_documents(ctx.driver)}


@router.post("/documents")
def upload_document(
    body: DocumentUploadRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    try:
        doc = svc.platform.documents.upload_document(
            db, ctx.driver, doc_type=body.doc_type, file_url=body.file_url, metadata=body.metadata
        )
        db.commit()
        return doc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/profile/vehicle-photos")
def upload_vehicle_photo(
    body: DocumentUploadRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    photo = svc.platform.documents.upload_vehicle_photo(
        db, ctx.driver, file_url=body.file_url, metadata=body.metadata
    )
    db.commit()
    return photo


@router.get("/training")
def training(ctx: Annotated[DriverContext, Depends(get_driver_context)]):
    return {"modules": svc.platform.training.list_modules(ctx.driver)}


@router.post("/training/{module_id}/complete")
def complete_training(
    module_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    result = svc.platform.training.complete_module(db, ctx.driver, module_id)
    db.commit()
    return result


