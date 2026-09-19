"""merchant routes — dashboard_booking."""

from typing import Annotated

from fastapi import Header

from porterchain_api.merchant_engine.booking_service import (
    booking_value_error_detail,
    confirm_replay_payload,
    parse_idempotency_key,
)
from porterchain_api.merchant_engine.template_service import template_payload
from porterchain_api.routers.merchant._deps import (
    Annotated,
    BulkUploadResponse,
    Depends,
    File,
    HTTPException,
    MerchantBookDeliveryRequest,
    MerchantBookingConfirmRequest,
    MerchantBookingConfirmResponse,
    MerchantBookingDraftResponse,
    MerchantBookingPreviewResponse,
    MerchantBookingTemplateCreateRequest,
    MerchantBookingTemplateResponse,
    MerchantContext,
    MerchantDashboardResponse,
    MerchantMultiParcelRequest,
    MerchantMultiParcelResponse,
    MerchantOrderResponse,
    Query,
    RecipientResponse,
    SavedAddressResponse,
    Session,
    Settings,
    UploadFile,
    _booking,
    _booking_flow,
    _bulk,
    _dashboard,
    _handle_permission,
    _order_response,
    _saved_address_out,
    get_db,
    get_merchant_context,
    get_settings,
    require_module,
    router,
)


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
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> MerchantOrderResponse:
    """Single-shot create. Send `Idempotency-Key` so a retry replays (BH)."""
    try:
        require_module(ctx, "book")
        key = parse_idempotency_key(idempotency_key)
        order = _booking.run_idempotent(
            db,
            ctx,
            key,
            lambda: _booking.create_shipment(
                db,
                settings,
                ctx,
                body,
                idempotency_key=key,
                sandbox=bool(getattr(body, "is_sandbox", False)),
            ),
            is_sandbox=bool(getattr(body, "is_sandbox", False)),
        )
        return _order_response(order)
    except PermissionError as exc:
        _handle_permission(exc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> MerchantBookingConfirmResponse:
    try:
        require_module(ctx, "book")
        key = parse_idempotency_key(idempotency_key)
        result = _booking.run_idempotent(
            db,
            ctx,
            key,
            lambda: _booking_flow.confirm_booking(
                db,
                settings,
                ctx,
                body.booking,
                draft_id=body.draft_id,
                idempotency_key=key,
            ),
            replay_map=confirm_replay_payload,
            is_sandbox=bool(getattr(body.booking, "is_sandbox", False)),
        )
        return MerchantBookingConfirmResponse(**result)
    except PermissionError as exc:
        _handle_permission(exc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=booking_value_error_detail(exc)) from exc
    except LookupError:
        raise HTTPException(status_code=404, detail="recipient_not_found") from None


@router.post("/booking/multi", response_model=MerchantMultiParcelResponse)
def booking_multi(
    body: MerchantMultiParcelRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> MerchantMultiParcelResponse:
    """One key covers the batch; each parcel is deduped from it (BH)."""
    try:
        require_module(ctx, "book")
        key = parse_idempotency_key(idempotency_key, max_len=96)
        result = _booking_flow.confirm_multi(
            db,
            settings,
            ctx,
            body.pickup,
            body.parcels,
            idempotency_key=key,
        )
        return MerchantMultiParcelResponse(**result)
    except PermissionError as exc:
        _handle_permission(exc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
        raise HTTPException(status_code=400, detail=booking_value_error_detail(exc)) from exc


@router.get("/booking/templates", response_model=list[MerchantBookingTemplateResponse])
def booking_list_templates(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[MerchantBookingTemplateResponse]:
    try:
        require_module(ctx, "book")
        templates = _booking_flow.list_templates(db, ctx)
        return [MerchantBookingTemplateResponse(**template_payload(t)) for t in templates]
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
        return MerchantBookingTemplateResponse(**template_payload(record))
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
        return [_saved_address_out(r) for r in rows]
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
        return BulkUploadResponse(**_bulk.upload_payload(job))
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
    is_sandbox: bool = Query(False),
) -> BulkUploadResponse:
    try:
        require_module(ctx, "bulk")
        job = _bulk.confirm_bulk(db, settings, ctx, job_id, is_sandbox=is_sandbox)
        return BulkUploadResponse(**_bulk.upload_payload(job))
    except LookupError:
        raise HTTPException(status_code=404, detail="bulk_job_not_found") from None
    except PermissionError as exc:
        _handle_permission(exc)


