"""admin routes — booking drafts."""

from porterchain_api.routers.admin._deps import (
    AdminContext,
    AdminDraftFilters,
    Annotated,
    BookingDraftAbandonedItem,
    BookingDraftAdminDetailResponse,
    BookingDraftAdminItem,
    BookingDraftAnalyticsResponse,
    BookingDraftBulkRequest,
    BookingDraftCancelRequest,
    BookingDraftExtendRequest,
    BookingDraftPaymentLinkResponse,
    Depends,
    HTTPException,
    Session,
    Settings,
    _draft_admin,
    commit_admin_audit,
    get_admin_context,
    get_db,
    get_settings,
    require_module,
    router,
)


def _draft_detail(
    db: Session,
    settings: Settings,
    draft_id: str,
) -> BookingDraftAdminDetailResponse:
    detail = _draft_admin.get_detail(db, settings, draft_id)
    if not detail:
        raise HTTPException(status_code=404, detail="draft_not_found")
    return BookingDraftAdminDetailResponse(**detail)


def _finish_draft(
    db: Session,
    ctx: AdminContext,
    settings: Settings,
    draft_id: str,
    *,
    action: str,
    payload: dict | None = None,
) -> BookingDraftAdminDetailResponse:
    commit_admin_audit(
        db,
        ctx,
        action=action,
        resource_type="booking_draft",
        resource_id=draft_id,
        payload=payload,
    )
    return _draft_detail(db, settings, draft_id)


@router.get("/booking-drafts/analytics", response_model=BookingDraftAnalyticsResponse)
def booking_draft_analytics(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> BookingDraftAnalyticsResponse:
    require_module(ctx, "bookings")
    return BookingDraftAnalyticsResponse(**_draft_admin.analytics(db))


@router.get("/booking-drafts/abandoned", response_model=list[BookingDraftAbandonedItem])
def booking_draft_abandoned(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[BookingDraftAbandonedItem]:
    require_module(ctx, "bookings")
    return [BookingDraftAbandonedItem(**row) for row in _draft_admin.abandoned(db)]


@router.get("/booking-drafts", response_model=list[BookingDraftAdminItem])
def list_booking_drafts(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    state: str | None = None,
    search: str | None = None,
    customer_id: str | None = None,
    merchant_id: str | None = None,
    booking_type: str | None = None,
    vehicle_class: str | None = None,
    payment_status: str | None = None,
    current_step: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    price_min_cents: int | None = None,
    price_max_cents: int | None = None,
    expired_only: bool = False,
    abandoned_only: bool = False,
) -> list[BookingDraftAdminItem]:
    require_module(ctx, "bookings")
    from datetime import datetime

    filters = AdminDraftFilters(
        state=state,
        search=search,
        customer_id=customer_id,
        merchant_id=merchant_id,
        booking_type=booking_type,
        vehicle_class=vehicle_class,
        payment_status=payment_status,
        current_step=current_step,
        date_from=datetime.fromisoformat(date_from) if date_from else None,
        date_to=datetime.fromisoformat(date_to) if date_to else None,
        price_min_cents=price_min_cents,
        price_max_cents=price_max_cents,
        expired_only=expired_only,
        abandoned_only=abandoned_only,
    )
    return [BookingDraftAdminItem(**row) for row in _draft_admin.list_drafts(db, filters)]


@router.get("/booking-drafts/{draft_id}", response_model=BookingDraftAdminDetailResponse)
def get_booking_draft_detail(
    draft_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> BookingDraftAdminDetailResponse:
    require_module(ctx, "bookings")
    return _draft_detail(db, settings, draft_id)


@router.post("/booking-drafts/{draft_id}/extend", response_model=BookingDraftAdminDetailResponse)
def extend_booking_draft(
    draft_id: str,
    body: BookingDraftExtendRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> BookingDraftAdminDetailResponse:
    require_module(ctx, "bookings")
    _draft_admin.extend_draft(
        db, settings, draft_id, extra_minutes=body.extra_minutes, actor_id=ctx.user.id
    )
    return _finish_draft(
        db,
        ctx,
        settings,
        draft_id,
        action="booking_draft.extend",
        payload={"extra_minutes": body.extra_minutes},
    )


@router.post("/booking-drafts/{draft_id}/cancel", response_model=BookingDraftAdminDetailResponse)
def cancel_booking_draft(
    draft_id: str,
    body: BookingDraftCancelRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> BookingDraftAdminDetailResponse:
    require_module(ctx, "bookings")
    try:
        _draft_admin.cancel_draft(db, draft_id, actor_id=ctx.user.id, reason=body.reason)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="draft_not_found") from exc
    return _finish_draft(
        db,
        ctx,
        settings,
        draft_id,
        action="booking_draft.cancel",
        payload={"reason": body.reason},
    )


@router.post("/booking-drafts/{draft_id}/restore", response_model=BookingDraftAdminDetailResponse)
def restore_booking_draft(
    draft_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> BookingDraftAdminDetailResponse:
    require_module(ctx, "bookings")
    try:
        _draft_admin.restore(db, settings, draft_id, actor_id=ctx.user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="draft_not_found") from exc
    return _finish_draft(db, ctx, settings, draft_id, action="booking_draft.restore")


@router.post("/booking-drafts/{draft_id}/expire", response_model=BookingDraftAdminDetailResponse)
def expire_booking_draft(
    draft_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> BookingDraftAdminDetailResponse:
    require_module(ctx, "bookings")
    try:
        _draft_admin.force_expire(db, draft_id, actor_id=ctx.user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="draft_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _finish_draft(db, ctx, settings, draft_id, action="booking_draft.expire")


@router.post("/booking-drafts/{draft_id}/duplicate", response_model=BookingDraftAdminDetailResponse)
def duplicate_booking_draft(
    draft_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> BookingDraftAdminDetailResponse:
    require_module(ctx, "bookings")
    try:
        clone = _draft_admin.duplicate(db, settings, draft_id, actor_id=ctx.user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="draft_not_found") from exc
    commit_admin_audit(
        db,
        ctx,
        action="booking_draft.duplicate",
        resource_type="booking_draft",
        resource_id=draft_id,
        payload={"clone_id": clone.id},
    )
    return _draft_detail(db, settings, clone.id)


@router.post("/booking-drafts/{draft_id}/send-payment-link", response_model=BookingDraftPaymentLinkResponse)
def send_payment_link(
    draft_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> BookingDraftPaymentLinkResponse:
    require_module(ctx, "bookings")
    try:
        result = _draft_admin.send_payment_link(db, settings, draft_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="draft_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    commit_admin_audit(
        db, ctx, action="booking_draft.send_payment_link", resource_type="booking_draft", resource_id=draft_id
    )
    return BookingDraftPaymentLinkResponse(**result)


@router.post("/booking-drafts/bulk")
def bulk_booking_draft_action(
    body: BookingDraftBulkRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    require_module(ctx, "bookings")
    result = _draft_admin.bulk_action(
        db,
        settings,
        draft_ids=body.draft_ids,
        action=body.action,
        actor_id=ctx.user.id,
        extra_minutes=body.extra_minutes,
        reason=body.reason,
    )
    commit_admin_audit(
        db,
        ctx,
        action=f"booking_draft.bulk_{body.action}",
        resource_type="booking_draft",
        resource_id=None,
        payload={"count": len(body.draft_ids)},
    )
    return result
