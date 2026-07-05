"""merchant routes — dashboard_booking."""

from porterchain_api.routers.merchant._deps import *  # noqa: F403

@router.get("/dashboard", response_model=MerchantDashboardResponse)
def merchant_dashboard(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantDashboardResponse:
    require_module(ctx, "dashboard")
    return MerchantDashboardResponse(**_dashboard.get_dashboard(db, ctx))


@router.post("/bookings", response_model=MerchantOrderResponse)
def create_booking(
    body: MerchantBookDeliveryRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MerchantOrderResponse:
    try:
        require_module(ctx, "book")
        order = _booking.create_shipment(db, settings, ctx, body)
        return _order_response(order)
    except PermissionError as exc:
        _handle_permission(exc)


@router.post("/booking/preview", response_model=MerchantBookingPreviewResponse)
def booking_preview(
    body: MerchantBookDeliveryRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MerchantBookingPreviewResponse:
    try:
        require_module(ctx, "book")
        return MerchantBookingPreviewResponse(**_booking_flow.preview(db, settings, ctx, body))
    except PermissionError as exc:
        _handle_permission(exc)
    except LookupError:
        raise HTTPException(status_code=404, detail="recipient_not_found") from None


@router.post("/booking/confirm", response_model=MerchantBookingConfirmResponse)
def booking_confirm(
    body: MerchantBookingConfirmRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MerchantBookingConfirmResponse:
    try:
        require_module(ctx, "book")
        result = _booking_flow.confirm_booking(
            db, settings, ctx, body.booking, draft_id=body.draft_id
        )
        return MerchantBookingConfirmResponse(**result)
    except PermissionError as exc:
        _handle_permission(exc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError:
        raise HTTPException(status_code=404, detail="recipient_not_found") from None


@router.post("/booking/multi", response_model=MerchantMultiParcelResponse)
def booking_multi(
    body: MerchantMultiParcelRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MerchantMultiParcelResponse:
    try:
        require_module(ctx, "book")
        result = _booking_flow.confirm_multi(db, settings, ctx, body.pickup, body.parcels)
        return MerchantMultiParcelResponse(**result)
    except PermissionError as exc:
        _handle_permission(exc)


@router.get("/booking/draft", response_model=MerchantBookingDraftResponse | None)
def booking_get_draft(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantBookingDraftResponse | None:
    try:
        require_module(ctx, "book")
        draft = _booking_flow.get_active_draft(db, ctx)
        return MerchantBookingDraftResponse(**draft) if draft else None
    except PermissionError as exc:
        _handle_permission(exc)


@router.post("/booking/draft")
def booking_save_draft(
    body: MerchantBookDeliveryRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_step: str = Query(default="review"),
) -> dict:
    try:
        require_module(ctx, "book")
        return _booking_flow.save_draft(db, settings, ctx, body, current_step=current_step)
    except PermissionError as exc:
        _handle_permission(exc)
    except LookupError:
        raise HTTPException(status_code=404, detail="recipient_not_found") from None


@router.post("/booking/draft/{draft_id}/confirm", response_model=MerchantOrderResponse)
def booking_confirm_draft(
    draft_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MerchantOrderResponse:
    try:
        require_module(ctx, "book")
        order = _booking_flow.confirm_draft(db, settings, ctx, draft_id)
        return _order_response(order)
    except PermissionError as exc:
        _handle_permission(exc)
    except LookupError:
        raise HTTPException(status_code=404, detail="draft_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/booking/templates", response_model=list[MerchantBookingTemplateResponse])
def booking_list_templates(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[MerchantBookingTemplateResponse]:
    try:
        require_module(ctx, "book")
        templates = _booking_flow.list_templates(db, ctx)
        return [
            MerchantBookingTemplateResponse(
                id=t.id,
                name=t.name,
                payload=t.payload,
                is_recurring=t.is_recurring,
                recurrence_rule=t.recurrence_rule,
                created_at=t.created_at,
            )
            for t in templates
        ]
    except PermissionError as exc:
        _handle_permission(exc)


@router.post("/booking/templates", response_model=MerchantBookingTemplateResponse)
def booking_create_template(
    body: MerchantBookingTemplateCreateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantBookingTemplateResponse:
    try:
        require_module(ctx, "book")
        record = _booking_flow.save_template(
            db,
            ctx,
            name=body.name,
            payload=body.payload,
            is_recurring=body.is_recurring,
            recurrence_rule=body.recurrence_rule,
        )
        return MerchantBookingTemplateResponse(
            id=record.id,
            name=record.name,
            payload=record.payload,
            is_recurring=record.is_recurring,
            recurrence_rule=record.recurrence_rule,
            created_at=record.created_at,
        )
    except PermissionError as exc:
        _handle_permission(exc)


@router.delete("/booking/templates/{template_id}", status_code=204)
def booking_delete_template(
    template_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> None:
    try:
        require_module(ctx, "book")
        _booking_flow.delete_template(db, ctx, template_id)
    except PermissionError as exc:
        _handle_permission(exc)
    except LookupError:
        raise HTTPException(status_code=404, detail="template_not_found") from None


@router.get("/booking/saved-addresses", response_model=list[SavedAddressResponse])
def booking_saved_addresses(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[SavedAddressResponse]:
    try:
        require_module(ctx, "book")
        rows = _booking_flow.list_saved_addresses(db, ctx)
        return [
            SavedAddressResponse(
                id=r.id,
                label=r.label,
                address_type=r.address_type,
                formatted=r.formatted,
                is_default=r.is_default,
            )
            for r in rows
        ]
    except PermissionError as exc:
        _handle_permission(exc)


@router.get("/booking/recipients", response_model=list[RecipientResponse])
def booking_recipients(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[RecipientResponse]:
    try:
        require_module(ctx, "book")
        rows = _booking_flow.list_recipients(db, ctx)
        return [
            RecipientResponse(
                id=r.id,
                name=r.name,
                email=r.email,
                phone=r.phone,
                company=r.company,
            )
            for r in rows
        ]
    except PermissionError as exc:
        _handle_permission(exc)


@router.post("/bulk/upload", response_model=BulkUploadResponse)
async def bulk_upload(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    file: UploadFile = File(...),
) -> BulkUploadResponse:
    try:
        require_module(ctx, "bulk")
        raw = await file.read()
        job = _bulk.upload_file(
            db,
            settings,
            ctx,
            filename=file.filename or "upload.csv",
            content=raw,
        )
        return BulkUploadResponse(
            job_id=job.id,
            status=job.status,
            total_rows=job.total_rows,
            valid_rows=job.valid_rows,
            error_rows=job.error_rows,
            duplicate_rows=job.duplicate_rows,
            preview=job.preview,
            errors=job.errors,
        )
    except PermissionError as exc:
        _handle_permission(exc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/bulk/{job_id}/confirm", response_model=BulkUploadResponse)
def bulk_confirm(
    job_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> BulkUploadResponse:
    try:
        require_module(ctx, "bulk")
        job = _bulk.confirm_bulk(db, settings, ctx, job_id)
        return BulkUploadResponse(
            job_id=job.id,
            status=job.status,
            total_rows=job.total_rows,
            valid_rows=job.valid_rows,
            error_rows=job.error_rows,
            duplicate_rows=job.duplicate_rows,
            preview=job.preview,
            errors=job.errors,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="bulk_job_not_found") from None
    except PermissionError as exc:
        _handle_permission(exc)


