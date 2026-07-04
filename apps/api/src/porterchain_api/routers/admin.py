"""Admin operations API — /v1/admin/*"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_engine.claims_service import AdminClaimsService, ClaimFilters
from porterchain_api.admin_engine.dashboard_service import AdminDashboardService
from porterchain_api.admin_engine.finance_service import AdminFinanceService, FinanceFilters
from porterchain_api.admin_engine.operations_service import AdminOperationsService
from porterchain_api.admin_engine.orders_service import AdminOrderFilters, AdminOrdersService
from porterchain_api.admin_engine.pricing_service import AdminPricingService, PricingFilters
from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.admin_engine.reports_service import AdminReportsService
from porterchain_api.admin_engine.clerk_directory_service import ClerkDirectoryService
from porterchain_api.admin_engine.settings_service import AdminSettingsService
from porterchain_api.admin_engine.support_service import AdminSupportService, SupportFilters
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.merchant_models import Merchant
from porterchain_api.models import Order
from porterchain_api.schemas_admin import (
    AdminDashboardResponse,
    AssignDriverRequest,
    ClaimCreateRequest,
    ClaimItem,
    ClaimListItem,
    ClaimDetailResponse,
    ClaimDashboardResponse,
    ClaimStatusUpdateRequest,
    ClaimAssignRequest,
    ClaimEvidenceRequest,
    ClaimNoteRequest,
    ClaimInvestigationRequest,
    ClaimCompensationRequest,
    ClaimInsuranceRequest,
    ClaimBulkRequest,
    OrderAdminItem,
    OrderListItem,
    OrderDashboardResponse,
    OrderDetailResponse,
    OrderDetail360Response,
    OrderBulkRequest,
    PaymentAdminItem,
    ReportsSummaryResponse,
    ReportSaveRequest,
    ReportScheduleRequest,
    ReportBuilderPreviewRequest,
    ReportExportAuditRequest,
    StaffItem,
    StaffInviteRequest,
    StaffInviteResponse,
    StaffRoleUpdateRequest,
    PlatformUserItem,
    PlatformUsersResponse,
    PlatformUserCreateRequest,
    PlatformUserUpdateRequest,
    PlatformUserDeleteRequest,
    SettingsConfigUpdateRequest,
    SettingsImportRequest,
    TariffCreateRequest,
    TariffUpdateRequest,
    PricingDashboardResponse,
    TariffItem,
    TicketCreateRequest,
    TicketItem,
    TicketListItem,
    TicketDetailResponse,
    TicketDashboardResponse,
    TicketStatusRequest,
    TicketAssignRequest,
    TicketNoteRequest,
    TicketBulkRequest,
    SupportKbArticleRequest,
    SupportMacroRequest,
    SupportAutomationRequest,
    SupportSlaConfigRequest,
    PromotionItem,
    PromotionCreateRequest,
    PricingZoneItem,
    PricingZoneCreateRequest,
    MerchantContractItem,
    MerchantContractCreateRequest,
    PricingSimulatorRequest,
    PricingBreakdownResponse,
    TaxConfigRequest,
    FuelConfigRequest,
    FinanceDashboardResponse,
    FinanceInvoiceItem,
    FinanceInvoiceDetailResponse,
    FinancePaymentItem,
    FinancePayoutItem,
    FinanceLedgerItem,
    FinanceCreditNoteRequest,
    BookingDraftAdminItem,
    BookingDraftAdminDetailResponse,
    BookingDraftAnalyticsResponse,
    BookingDraftAbandonedItem,
    BookingDraftExtendRequest,
    BookingDraftCancelRequest,
    BookingDraftBulkRequest,
    BookingDraftPaymentLinkResponse,
)
from porterchain_api.admin_engine.booking_draft_admin_service import (
    AdminBookingDraftService,
    AdminDraftFilters,
)
router = APIRouter(prefix="/v1/admin", tags=["admin"])

_dashboard = AdminDashboardService()
_ops = AdminOperationsService()
_orders = AdminOrdersService()
_claims = AdminClaimsService()
_pricing = AdminPricingService()
_finance = AdminFinanceService()
_support = AdminSupportService()
_reports = AdminReportsService()
_settings = AdminSettingsService()
_clerk_directory = ClerkDirectoryService()
_draft_admin = AdminBookingDraftService()


def _perm(exc: PermissionError) -> None:
    raise HTTPException(status_code=403, detail=str(exc)) from exc


def _order_item(o: Order) -> OrderAdminItem:
    return OrderAdminItem(
        order_id=o.id,
        order_number=o.order_number,
        tracking_number=o.tracking_number,
        state=o.state,
        amount_cents=o.amount_cents,
        currency=o.currency,
        merchant_id=o.merchant_id,
        customer_id=o.customer_id,
        scheduled_at=o.scheduled_at,
        pickup=o.pickup,
        dropoff=o.dropoff,
        created_at=o.created_at,
    )


def _order_detail(detail: dict) -> OrderDetailResponse:
    order: Order = detail["order"]
    quote = detail.get("quote")
    booking = detail.get("booking")
    invoice = detail.get("invoice")
    customer = detail.get("customer")
    payments = detail.get("payments") or []

    return OrderDetailResponse(
        order_id=order.id,
        order_number=order.order_number,
        tracking_number=order.tracking_number,
        state=order.state,
        amount_cents=order.amount_cents,
        currency=order.currency,
        scheduled_at=order.scheduled_at,
        created_at=order.created_at,
        pickup=order.pickup,
        dropoff=order.dropoff,
        special_instructions=order.special_instructions,
        fleetbase_order_id=order.fleetbase_order_id,
        assigned_driver_id=order.assigned_driver_id,
        customer_id=order.customer_id,
        customer_email=customer.email if customer else None,
        customer_phone=customer.phone if customer else None,
        booking_number=booking.booking_number if booking else None,
        quote_id=quote.id if quote else None,
        vehicle_class=quote.vehicle_class if quote else None,
        package_type=quote.package_type if quote else None,
        weight_kg=quote.weight_kg if quote else None,
        dimensions=quote.dimensions if quote else None,
        declared_value_cents=quote.declared_value_cents if quote else None,
        distance_meters=quote.distance_meters if quote else None,
        quote_amount_cents=quote.amount_cents if quote else None,
        pricing_breakdown=quote.pricing_breakdown if quote else None,
        payments=[
            PaymentAdminItem(
                payment_id=p.id,
                status=p.status,
                amount_cents=p.amount_cents,
                currency=p.currency,
                stripe_payment_intent_id=p.stripe_payment_intent_id,
                stripe_checkout_session_id=p.stripe_checkout_session_id,
                receipt_url=p.receipt_url,
                failure_reason=p.failure_reason,
                retry_count=p.retry_count,
                created_at=p.created_at,
            )
            for p in payments
        ],
        invoice_number=invoice.invoice_number if invoice else None,
        invoice_amount_cents=invoice.amount_cents if invoice else None,
        invoice_receipt_url=invoice.stripe_receipt_url if invoice else None,
        invoice_pdf_url=invoice.pdf_url if invoice else None,
    )


@router.get("/dashboard", response_model=AdminDashboardResponse)
def admin_dashboard(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> AdminDashboardResponse:
    require_module(ctx, "dashboard")
    return AdminDashboardResponse(**_dashboard.get_dashboard(db))


@router.get("/dashboard/center")
def dashboard_center(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "dashboard")
    return _dashboard.get_center(db, settings, role=ctx.role.value)


@router.get("/dashboard/search")
def dashboard_search(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    q: str = Query(min_length=2),
):
    require_module(ctx, "dashboard")
    return _dashboard.global_search(db, q)


@router.get("/dispatch/queue", response_model=list[OrderAdminItem])
def dispatch_queue(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[OrderAdminItem]:
    require_module(ctx, "dispatch_read")
    return [_order_item(o) for o in _ops.dispatch_queue(db)]


@router.post("/dispatch/orders/{order_id}/assign", response_model=OrderAdminItem)
def assign_driver(
    order_id: str,
    body: AssignDriverRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OrderAdminItem:
    require_module(ctx, "dispatch")
    try:
        o = _ops.assign_driver(db, settings, ctx, order_id, body.driver_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _order_item(o)


@router.get("/map/live")
def live_map(ctx: Annotated[AdminContext, Depends(get_admin_context)], db: Session = Depends(get_db)):
    require_module(ctx, "map")
    return _ops.live_map_snapshot(db)


@router.get("/orders/dashboard", response_model=OrderDashboardResponse)
def orders_dashboard(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> OrderDashboardResponse:
    require_module(ctx, "orders_read")
    return OrderDashboardResponse(**_orders.dashboard(db))


@router.get("/orders/reports")
def orders_reports(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "orders_read")
    return _orders.reports(db)


@router.get("/orders", response_model=list[OrderListItem])
def list_orders(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    state: str | None = None,
    payment_status: str | None = None,
    invoice_status: str | None = None,
    merchant_id: str | None = None,
    driver_id: str | None = None,
    priority: str | None = None,
    service_type: str | None = None,
    city: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    amount_min_cents: int | None = None,
    amount_max_cents: int | None = None,
    limit: int = 500,
    offset: int = 0,
) -> list[OrderListItem]:
    require_module(ctx, "orders_read")
    from datetime import datetime

    filters = AdminOrderFilters(
        state=state,
        payment_status=payment_status,
        invoice_status=invoice_status,
        merchant_id=merchant_id,
        driver_id=driver_id,
        priority=priority,
        service_type=service_type,
        city=city,
        search=search,
        date_from=datetime.fromisoformat(date_from) if date_from else None,
        date_to=datetime.fromisoformat(date_to) if date_to else None,
        amount_min_cents=amount_min_cents,
        amount_max_cents=amount_max_cents,
        limit=limit,
        offset=offset,
    )
    return [OrderListItem(**row) for row in _orders.list_enriched(db, filters)]


@router.post("/orders/bulk")
def orders_bulk(
    body: OrderBulkRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    require_module(ctx, "orders_write")
    results = _orders.bulk_action(
        db,
        settings,
        ctx,
        body.order_ids,
        body.action,
        driver_id=body.driver_id,
    )
    return {"results": results}


@router.get("/orders/{order_id}", response_model=OrderDetail360Response)
def get_order_detail(
    order_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OrderDetail360Response:
    require_module(ctx, "orders_read")
    detail = _orders.get_detail_360(db, settings, order_id)
    if not detail:
        raise HTTPException(status_code=404, detail="order_not_found")
    return OrderDetail360Response(**detail)


@router.get("/orders/{order_id}/tracking")
def get_order_tracking(
    order_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    require_module(ctx, "orders_read")
    tracking = _orders.order_tracking(db, settings, order_id)
    if not tracking:
        raise HTTPException(status_code=404, detail="order_not_found")
    return tracking


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
    detail = _draft_admin.get_detail(db, settings, draft_id)
    if not detail:
        raise HTTPException(status_code=404, detail="draft_not_found")
    return BookingDraftAdminDetailResponse(**detail)


@router.post("/booking-drafts/{draft_id}/extend", response_model=BookingDraftAdminDetailResponse)
def extend_booking_draft(
    draft_id: str,
    body: BookingDraftExtendRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> BookingDraftAdminDetailResponse:
    require_module(ctx, "bookings")
    draft = _draft_admin.extend_draft(
        db, settings, draft_id, extra_minutes=body.extra_minutes, actor_id=ctx.user.id
    )
    log_admin_audit(
        db,
        ctx,
        action="booking_draft.extend",
        resource_type="booking_draft",
        resource_id=draft_id,
        payload={"extra_minutes": body.extra_minutes},
    )
    db.commit()
    return get_booking_draft_detail(draft_id, ctx, db, settings)


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
    log_admin_audit(
        db,
        ctx,
        action="booking_draft.cancel",
        resource_type="booking_draft",
        resource_id=draft_id,
        payload={"reason": body.reason},
    )
    db.commit()
    return get_booking_draft_detail(draft_id, ctx, db, settings)


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
    log_admin_audit(db, ctx, action="booking_draft.restore", resource_type="booking_draft", resource_id=draft_id)
    db.commit()
    return get_booking_draft_detail(draft_id, ctx, db, settings)


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
    log_admin_audit(db, ctx, action="booking_draft.expire", resource_type="booking_draft", resource_id=draft_id)
    db.commit()
    return get_booking_draft_detail(draft_id, ctx, db, settings)


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
    log_admin_audit(
        db,
        ctx,
        action="booking_draft.duplicate",
        resource_type="booking_draft",
        resource_id=draft_id,
        payload={"clone_id": clone.id},
    )
    db.commit()
    return get_booking_draft_detail(clone.id, ctx, db, settings)


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
    log_admin_audit(db, ctx, action="booking_draft.send_payment_link", resource_type="booking_draft", resource_id=draft_id)
    db.commit()
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
    log_admin_audit(
        db,
        ctx,
        action=f"booking_draft.bulk_{body.action}",
        resource_type="booking_draft",
        resource_id=None,
        payload={"count": len(body.draft_ids)},
    )
    db.commit()
    return result


@router.get("/orders/{order_id}/timeline")
def order_timeline(
    order_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "orders_read")
    events = _orders.order_timeline(db, order_id)
    return [
        {
            "event_type": e.event_type,
            "from_state": e.from_state,
            "to_state": e.to_state,
            "occurred_at": e.occurred_at.isoformat(),
            "payload": e.payload,
        }
        for e in events
    ]


@router.get("/claims/dashboard", response_model=ClaimDashboardResponse)
def claims_dashboard(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ClaimDashboardResponse:
    require_module(ctx, "claims_read")
    return ClaimDashboardResponse(**_claims.dashboard(db))


@router.get("/claims/reports")
def claims_reports(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "claims_read")
    return _claims.reports(db)


@router.get("/claims", response_model=list[ClaimListItem])
def list_claims(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    status: str | None = None,
    claim_type: str | None = None,
    priority: str | None = None,
    investigator_id: str | None = None,
    merchant_id: str | None = None,
    driver_id: str | None = None,
    insurance: bool | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    amount_min_cents: int | None = None,
    amount_max_cents: int | None = None,
    risk_min: int | None = None,
    search: str | None = None,
) -> list[ClaimListItem]:
    require_module(ctx, "claims_read")
    from datetime import datetime

    filters = ClaimFilters(
        status=status,
        claim_type=claim_type,
        priority=priority,
        investigator_id=investigator_id,
        merchant_id=merchant_id,
        driver_id=driver_id,
        insurance=insurance,
        date_from=datetime.fromisoformat(date_from) if date_from else None,
        date_to=datetime.fromisoformat(date_to) if date_to else None,
        amount_min_cents=amount_min_cents,
        amount_max_cents=amount_max_cents,
        risk_min=risk_min,
        search=search,
    )
    return [ClaimListItem(**row) for row in _claims.list_enriched(db, filters)]


@router.get("/claims/{claim_id}", response_model=ClaimDetailResponse)
def get_claim_detail(
    claim_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ClaimDetailResponse:
    require_module(ctx, "claims_read")
    detail = _claims.get_detail(db, claim_id)
    if not detail:
        raise HTTPException(status_code=404, detail="claim_not_found")
    return ClaimDetailResponse(**detail)


@router.post("/claims", response_model=ClaimListItem)
def create_claim(
    body: ClaimCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ClaimListItem:
    require_module(ctx, "claims")
    c = _claims.open_claim(
        db,
        ctx,
        order_id=body.order_id,
        claim_type=body.claim_type,
        description=body.description,
        priority=body.priority,
    )
    log_admin_audit(db, ctx, action="claim.create", resource_type="claim", resource_id=c.id)
    db.commit()
    return ClaimListItem(**_claims.claim_row(db, c))


@router.post("/claims/{claim_id}/status", response_model=ClaimDetailResponse)
def update_claim_status(
    claim_id: str,
    body: ClaimStatusUpdateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ClaimDetailResponse:
    require_module(ctx, "claims")
    try:
        _claims.update_status(db, ctx, claim_id, body.status)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="claim_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log_admin_audit(db, ctx, action="claim.status", resource_type="claim", resource_id=claim_id, payload={"status": body.status})
    db.commit()
    return get_claim_detail(claim_id, ctx, db)


@router.post("/claims/{claim_id}/assign", response_model=ClaimDetailResponse)
def assign_claim(
    claim_id: str,
    body: ClaimAssignRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ClaimDetailResponse:
    require_module(ctx, "claims")
    try:
        _claims.assign_investigator(db, ctx, claim_id, body.investigator_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="claim_not_found") from exc
    log_admin_audit(db, ctx, action="claim.assign", resource_type="claim", resource_id=claim_id)
    db.commit()
    return get_claim_detail(claim_id, ctx, db)


@router.post("/claims/{claim_id}/auto-assign", response_model=ClaimDetailResponse)
def auto_assign_claim(
    claim_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ClaimDetailResponse:
    require_module(ctx, "claims")
    try:
        _claims.auto_assign_investigator(db, ctx, claim_id)
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return get_claim_detail(claim_id, ctx, db)


@router.post("/claims/{claim_id}/evidence", response_model=ClaimDetailResponse)
def add_claim_evidence(
    claim_id: str,
    body: ClaimEvidenceRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ClaimDetailResponse:
    require_module(ctx, "claims")
    try:
        _claims.add_evidence(
            db, ctx, claim_id, file_type=body.file_type, name=body.name, url=body.url, meta=body.meta
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="claim_not_found") from exc
    db.commit()
    return get_claim_detail(claim_id, ctx, db)


@router.post("/claims/{claim_id}/notes", response_model=ClaimDetailResponse)
def add_claim_note(
    claim_id: str,
    body: ClaimNoteRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ClaimDetailResponse:
    require_module(ctx, "claims")
    try:
        _claims.add_note(db, ctx, claim_id, body=body.body, internal=body.internal, channel=body.channel)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="claim_not_found") from exc
    db.commit()
    return get_claim_detail(claim_id, ctx, db)


@router.post("/claims/{claim_id}/investigation", response_model=ClaimDetailResponse)
def update_claim_investigation(
    claim_id: str,
    body: ClaimInvestigationRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ClaimDetailResponse:
    require_module(ctx, "claims")
    try:
        _claims.update_investigation(db, ctx, claim_id, body.model_dump(exclude_none=True))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="claim_not_found") from exc
    db.commit()
    return get_claim_detail(claim_id, ctx, db)


@router.post("/claims/{claim_id}/compensation", response_model=ClaimDetailResponse)
def set_claim_compensation(
    claim_id: str,
    body: ClaimCompensationRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ClaimDetailResponse:
    require_module(ctx, "claims")
    try:
        _claims.set_compensation(db, ctx, claim_id, body.model_dump(exclude_none=True))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="claim_not_found") from exc
    db.commit()
    return get_claim_detail(claim_id, ctx, db)


@router.post("/claims/{claim_id}/insurance", response_model=ClaimDetailResponse)
def set_claim_insurance(
    claim_id: str,
    body: ClaimInsuranceRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ClaimDetailResponse:
    require_module(ctx, "claims")
    try:
        _claims.set_insurance(db, ctx, claim_id, body.model_dump(exclude_none=True))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="claim_not_found") from exc
    db.commit()
    return get_claim_detail(claim_id, ctx, db)


@router.post("/claims/bulk")
def bulk_claim_action(
    body: ClaimBulkRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "claims")
    result = _claims.bulk_action(
        db,
        ctx,
        claim_ids=body.claim_ids,
        action=body.action,
        investigator_id=body.investigator_id,
        status=body.status,
    )
    log_admin_audit(db, ctx, action=f"claim.bulk_{body.action}", resource_type="claim", resource_id=None)
    db.commit()
    return result


@router.get("/pricing/dashboard", response_model=PricingDashboardResponse)
def pricing_dashboard(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> PricingDashboardResponse:
    require_module(ctx, "pricing_read")
    return PricingDashboardResponse(**_pricing.dashboard(db))


@router.get("/pricing/reports")
def pricing_reports(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "pricing_read")
    return _pricing.reports(db)


@router.get("/pricing/conflicts")
def pricing_conflicts(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[dict]:
    require_module(ctx, "pricing_read")
    return _pricing.detect_conflicts(db)


@router.get("/pricing/tariffs", response_model=list[TariffItem])
def list_tariffs(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    tariff_type: str | None = None,
    vehicle_class: str | None = None,
    merchant_id: str | None = None,
    zone: str | None = None,
    status: str | None = None,
    search: str | None = None,
    include_inactive: bool = False,
) -> list[TariffItem]:
    require_module(ctx, "pricing_read")
    filters = PricingFilters(
        tariff_type=tariff_type,
        vehicle_class=vehicle_class,
        merchant_id=merchant_id,
        zone=zone,
        status=status,
        search=search,
        include_inactive=include_inactive,
    )
    return [TariffItem(**row) for row in _pricing.list_tariffs_enriched(db, filters)]


@router.post("/pricing/tariffs", response_model=TariffItem)
def create_tariff(
    body: TariffCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TariffItem:
    require_module(ctx, "pricing")
    t = _pricing.create_tariff(db, ctx, **body.model_dump())
    merchants = {m.id: m.company_name for m in db.query(Merchant).all()}
    meta = dict((t.config or {}).get("_meta") or {})
    return TariffItem(**_pricing._tariff_row(t, merchants, meta, meta.get("status", "draft")))


@router.patch("/pricing/tariffs/{tariff_id}", response_model=TariffItem)
def update_tariff(
    tariff_id: str,
    body: TariffUpdateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TariffItem:
    require_module(ctx, "pricing")
    try:
        t = _pricing.update_tariff(db, ctx, tariff_id, **body.model_dump(exclude_none=True))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    merchants = {m.id: m.company_name for m in db.query(Merchant).all()}
    meta = dict((t.config or {}).get("_meta") or {})
    return TariffItem(**_pricing._tariff_row(t, merchants, meta, meta.get("status", "published")))


@router.post("/pricing/tariffs/{tariff_id}/publish", response_model=TariffItem)
def publish_tariff(
    tariff_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TariffItem:
    require_module(ctx, "pricing")
    try:
        t = _pricing.publish_tariff(db, ctx, tariff_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    merchants = {m.id: m.company_name for m in db.query(Merchant).all()}
    meta = dict((t.config or {}).get("_meta") or {})
    return TariffItem(**_pricing._tariff_row(t, merchants, meta, "published"))


@router.get("/pricing/promotions", response_model=list[PromotionItem])
def list_promotions(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[PromotionItem]:
    require_module(ctx, "pricing_read")
    return [PromotionItem(**row) for row in _pricing.list_promotions_enriched(db)]


@router.post("/pricing/promotions", response_model=PromotionItem)
def create_promotion(
    body: PromotionCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> PromotionItem:
    require_module(ctx, "pricing")
    p = _pricing.create_promotion(db, ctx, body.code, **body.model_dump(exclude={"code"}))
    row = next((r for r in _pricing.list_promotions_enriched(db) if r["id"] == p.id), None)
    if row:
        return PromotionItem(**row)
    return PromotionItem(
        id=p.id, code=p.code, promotion_type=p.promotion_type, merchant_id=p.merchant_id,
        discount_percent=p.discount_percent, discount_cents=p.discount_cents, is_active=p.is_active,
    )


@router.get("/pricing/zones", response_model=list[PricingZoneItem])
def list_pricing_zones(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[PricingZoneItem]:
    require_module(ctx, "pricing_read")
    return [PricingZoneItem(**row) for row in _pricing.list_zones_enriched(db)]


@router.post("/pricing/zones", response_model=PricingZoneItem)
def create_pricing_zone(
    body: PricingZoneCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> PricingZoneItem:
    require_module(ctx, "pricing")
    z = _pricing.create_zone(db, ctx, **body.model_dump())
    return PricingZoneItem(
        id=z.id, code=z.code, name=z.name, multiplier=z.multiplier, is_active=z.is_active,
        bounds=dict(z.bounds or {}), created_at=z.created_at,
    )


@router.get("/pricing/contracts", response_model=list[MerchantContractItem])
def list_merchant_contracts(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    merchant_id: str | None = None,
) -> list[MerchantContractItem]:
    require_module(ctx, "pricing_read")
    return [MerchantContractItem(**row) for row in _pricing.list_contracts_enriched(db, merchant_id=merchant_id)]


@router.post("/pricing/contracts", response_model=MerchantContractItem)
def create_merchant_contract(
    body: MerchantContractCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> MerchantContractItem:
    require_module(ctx, "pricing")
    c = _pricing.create_contract(db, ctx, **body.model_dump())
    row = next((r for r in _pricing.list_contracts_enriched(db) if r["id"] == c.id), None)
    if row:
        return MerchantContractItem(**row)
    return MerchantContractItem(
        id=c.id, merchant_id=c.merchant_id, name=c.name,
        minimum_monthly_commitment_cents=c.minimum_monthly_commitment_cents, is_active=c.is_active,
    )


@router.post("/pricing/simulate", response_model=PricingBreakdownResponse)
def simulate_pricing(
    body: PricingSimulatorRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> PricingBreakdownResponse:
    require_module(ctx, "pricing")
    result = _pricing.simulate(db, body.model_dump())
    return PricingBreakdownResponse(**result)


@router.get("/pricing/tax")
def get_tax_config(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "pricing_read")
    return _pricing.get_tax_config(db)


@router.put("/pricing/tax")
def update_tax_config(
    body: TaxConfigRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "pricing")
    return _pricing.update_tax_config(db, ctx, body.model_dump())


@router.get("/pricing/fuel")
def get_fuel_config(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "pricing_read")
    return _pricing.get_fuel_config(db)


@router.put("/pricing/fuel")
def update_fuel_config(
    body: FuelConfigRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "pricing")
    return _pricing.update_fuel_config(db, ctx, body.model_dump())


@router.get("/finance/dashboard", response_model=FinanceDashboardResponse)
def finance_dashboard(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> FinanceDashboardResponse:
    require_module(ctx, "finance_read")
    return FinanceDashboardResponse(**_finance.dashboard(db))


@router.get("/finance/reports")
def finance_reports(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "finance_read")
    return _finance.reports(db)


@router.get("/finance/collections", response_model=list[FinanceInvoiceItem])
def finance_collections(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[FinanceInvoiceItem]:
    require_module(ctx, "finance_read")
    return [FinanceInvoiceItem(**row) for row in _finance.collections(db)]


@router.get("/finance/export")
def finance_export_gl(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[dict]:
    require_module(ctx, "finance_read")
    return _finance.export_gl(db)


@router.get("/finance/invoices", response_model=list[FinanceInvoiceItem])
def finance_list_invoices(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    status: str | None = None,
    merchant_id: str | None = None,
    currency: str | None = None,
    search: str | None = None,
    outstanding_only: bool = False,
    date_from: str | None = None,
    date_to: str | None = None,
    amount_min_cents: int | None = None,
    amount_max_cents: int | None = None,
) -> list[FinanceInvoiceItem]:
    require_module(ctx, "finance_read")
    from datetime import datetime

    filters = FinanceFilters(
        status=status,
        merchant_id=merchant_id,
        currency=currency,
        search=search,
        outstanding_only=outstanding_only,
        date_from=datetime.fromisoformat(date_from) if date_from else None,
        date_to=datetime.fromisoformat(date_to) if date_to else None,
        amount_min_cents=amount_min_cents,
        amount_max_cents=amount_max_cents,
    )
    return [FinanceInvoiceItem(**row) for row in _finance.list_invoices_enriched(db, filters)]


@router.get("/finance/invoices/{invoice_id}", response_model=FinanceInvoiceDetailResponse)
def finance_invoice_detail(
    invoice_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> FinanceInvoiceDetailResponse:
    require_module(ctx, "finance_read")
    detail = _finance.get_invoice_detail(db, invoice_id)
    if not detail:
        raise HTTPException(status_code=404, detail="invoice_not_found")
    return FinanceInvoiceDetailResponse(**detail)


@router.get("/finance/payments", response_model=list[FinancePaymentItem])
def finance_list_payments(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    status: str | None = None,
    payment_method: str | None = None,
    search: str | None = None,
) -> list[FinancePaymentItem]:
    require_module(ctx, "finance_read")
    filters = FinanceFilters(status=status, payment_method=payment_method, search=search)
    return [FinancePaymentItem(**row) for row in _finance.list_payments_enriched(db, filters)]


@router.get("/finance/payouts", response_model=list[FinancePayoutItem])
def finance_list_payouts(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    status: str | None = None,
) -> list[FinancePayoutItem]:
    require_module(ctx, "finance_read")
    return [FinancePayoutItem(**row) for row in _finance.list_payouts_enriched(db, status=status)]


@router.get("/finance/ledger", response_model=list[FinanceLedgerItem])
def finance_ledger(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[FinanceLedgerItem]:
    require_module(ctx, "finance_read")
    return [FinanceLedgerItem(**row) for row in _finance.list_ledger(db)]


@router.get("/finance/duplicates")
def finance_duplicates(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "finance_read")
    return {"payments": _finance.find_duplicate_payments(db)}


@router.post("/finance/credit-notes")
def finance_credit_note(
    body: FinanceCreditNoteRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "finance")
    entry = _finance.record_credit_note(
        db, ctx, order_id=body.order_id, amount_cents=body.amount_cents, reason=body.reason
    )
    return {"ledger_id": entry.id, "status": entry.status}


@router.get("/finance/summary")
def finance_summary(ctx: Annotated[AdminContext, Depends(get_admin_context)], db: Session = Depends(get_db)):
    require_module(ctx, "finance_read")
    return _finance.revenue_summary(db)


@router.get("/support/dashboard", response_model=TicketDashboardResponse)
def support_dashboard(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TicketDashboardResponse:
    require_module(ctx, "support_read")
    return TicketDashboardResponse(**_support.dashboard(db))


@router.get("/support/reports")
def support_reports(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support_read")
    return _support.reports(db)


@router.get("/support/tickets", response_model=list[TicketListItem])
def list_tickets(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    status: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    agent_id: str | None = None,
    merchant_id: str | None = None,
    driver_id: str | None = None,
    customer_id: str | None = None,
    sla: str | None = None,
    module: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(500, le=1000),
) -> list[TicketListItem]:
    require_module(ctx, "support_read")
    from datetime import datetime

    filters = SupportFilters(
        status=status,
        category=category,
        priority=priority,
        agent_id=agent_id,
        merchant_id=merchant_id,
        driver_id=driver_id,
        customer_id=customer_id,
        sla=sla,
        module=module,
        search=search,
        date_from=datetime.fromisoformat(date_from) if date_from else None,
        date_to=datetime.fromisoformat(date_to) if date_to else None,
        limit=limit,
    )
    return [TicketListItem(**row) for row in _support.list_enriched(db, filters)]


@router.get("/support/tickets/{ticket_id}", response_model=TicketDetailResponse)
def get_ticket_detail(
    ticket_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TicketDetailResponse:
    require_module(ctx, "support_read")
    detail = _support.get_detail(db, ticket_id)
    if not detail:
        raise HTTPException(404, "ticket_not_found")
    return TicketDetailResponse(**detail)


@router.post("/support/tickets", response_model=TicketListItem)
def create_ticket(
    body: TicketCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TicketListItem:
    require_module(ctx, "support")
    t = _support.create_ticket(db, ctx, **body.model_dump())
    return TicketListItem(**_support._row(db, t))


@router.post("/support/tickets/{ticket_id}/status", response_model=TicketDetailResponse)
def update_ticket_status(
    ticket_id: str,
    body: TicketStatusRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TicketDetailResponse:
    require_module(ctx, "support")
    try:
        _support.update_status(db, ctx, ticket_id, body.status)
    except LookupError:
        raise HTTPException(404, "ticket_not_found") from None
    except ValueError:
        raise HTTPException(400, "invalid_status") from None
    detail = _support.get_detail(db, ticket_id)
    return TicketDetailResponse(**detail)


@router.post("/support/tickets/{ticket_id}/assign", response_model=TicketDetailResponse)
def assign_ticket(
    ticket_id: str,
    body: TicketAssignRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TicketDetailResponse:
    require_module(ctx, "support")
    try:
        _support.assign_agent(db, ctx, ticket_id, body.agent_id)
    except LookupError:
        raise HTTPException(404, "ticket_not_found") from None
    detail = _support.get_detail(db, ticket_id)
    return TicketDetailResponse(**detail)


@router.post("/support/tickets/{ticket_id}/auto-assign", response_model=TicketDetailResponse)
def auto_assign_ticket(
    ticket_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TicketDetailResponse:
    require_module(ctx, "support")
    try:
        _support.auto_assign(db, ctx, ticket_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None
    detail = _support.get_detail(db, ticket_id)
    return TicketDetailResponse(**detail)


@router.post("/support/tickets/{ticket_id}/notes", response_model=TicketDetailResponse)
def add_ticket_note(
    ticket_id: str,
    body: TicketNoteRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TicketDetailResponse:
    require_module(ctx, "support")
    try:
        _support.add_note(db, ctx, ticket_id, body=body.body, internal=body.internal, channel=body.channel)
    except LookupError:
        raise HTTPException(404, "ticket_not_found") from None
    detail = _support.get_detail(db, ticket_id)
    return TicketDetailResponse(**detail)


@router.post("/support/tickets/{ticket_id}/sla/pause", response_model=TicketDetailResponse)
def pause_ticket_sla(
    ticket_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TicketDetailResponse:
    require_module(ctx, "support")
    try:
        _support.pause_sla(db, ctx, ticket_id)
    except LookupError:
        raise HTTPException(404, "ticket_not_found") from None
    detail = _support.get_detail(db, ticket_id)
    return TicketDetailResponse(**detail)


@router.post("/support/tickets/{ticket_id}/sla/resume", response_model=TicketDetailResponse)
def resume_ticket_sla(
    ticket_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TicketDetailResponse:
    require_module(ctx, "support")
    try:
        _support.resume_sla(db, ctx, ticket_id)
    except LookupError:
        raise HTTPException(404, "ticket_not_found") from None
    detail = _support.get_detail(db, ticket_id)
    return TicketDetailResponse(**detail)


@router.post("/support/bulk")
def support_bulk(
    body: TicketBulkRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support")
    return {
        "results": _support.bulk_action(
            db,
            ctx,
            body.ticket_ids,
            body.action,
            agent_id=body.agent_id,
            status=body.status,
        )
    }


@router.get("/support/knowledge-base")
def get_support_kb(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support_read")
    return _support.get_knowledge_base(db)


@router.post("/support/knowledge-base/articles")
def save_support_kb_article(
    body: SupportKbArticleRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support")
    return _support.save_kb_article(db, ctx, body.model_dump())


@router.get("/support/macros")
def get_support_macros(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support_read")
    return _support.get_macros(db)


@router.post("/support/macros")
def save_support_macro(
    body: SupportMacroRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support")
    return _support.save_macro(db, ctx, body.model_dump())


@router.get("/support/automation")
def get_support_automation(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support_read")
    return _support.get_automation_rules(db)


@router.post("/support/automation")
def set_support_automation(
    body: SupportAutomationRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support")
    return _support.set_automation_rules(db, ctx, body.model_dump(exclude_none=True))


@router.get("/support/settings/sla")
def get_support_sla(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support_read")
    return _support._sla_config(db)


@router.post("/support/settings/sla")
def set_support_sla(
    body: SupportSlaConfigRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support")
    return _support.set_sla_config(db, ctx, body.model_dump(exclude_none=True))


@router.get("/reports/center")
def reports_center(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.center(db, role=ctx.role.value)


@router.get("/reports/executive")
def reports_executive(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.executive(db)


@router.get("/reports/categories")
def reports_categories(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
):
    require_module(ctx, "reports")
    from porterchain_api.admin_engine.reports_service import REPORT_CATEGORIES

    return REPORT_CATEGORIES


@router.get("/reports/category/{category_id}")
def reports_category(
    category_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.category_report(db, category_id)


@router.get("/reports/modules")
def reports_modules(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.module_bundle(db)


@router.get("/reports/trends")
def reports_trends(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    months: int = Query(12, le=24),
):
    require_module(ctx, "reports")
    return _reports.monthly_trends(db, months)


@router.get("/reports/delivery-performance")
def reports_delivery_performance(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.delivery_performance(db)


@router.get("/reports/smart")
def reports_smart(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.smart_insights(db)


@router.get("/reports/saved")
def reports_saved_list(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.list_saved_reports(db)


@router.post("/reports/saved")
def reports_saved_create(
    body: ReportSaveRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.save_report(
        db,
        ctx,
        name=body.name,
        category_id=body.category_id,
        chart_type=body.chart_type,
        filters=body.filters,
        pinned=body.pinned,
    )


@router.delete("/reports/saved/{report_id}")
def reports_saved_delete(
    report_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    _reports.delete_saved_report(db, ctx, report_id)
    return {"status": "deleted"}


@router.get("/reports/scheduled")
def reports_scheduled_list(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.list_scheduled_reports(db)


@router.post("/reports/scheduled")
def reports_scheduled_create(
    body: ReportScheduleRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.save_scheduled_report(
        db,
        ctx,
        name=body.name,
        category_id=body.category_id,
        schedule=body.schedule,
        email=body.email,
    )


@router.get("/reports/builder/datasets")
def reports_builder_datasets(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
):
    require_module(ctx, "reports")
    return _reports.builder_datasets()


@router.post("/reports/builder/preview")
def reports_builder_preview(
    body: ReportBuilderPreviewRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.builder_preview(db, dataset=body.dataset, group_by=body.group_by, metric=body.metric)


@router.post("/reports/export-audit")
def reports_export_audit(
    body: ReportExportAuditRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    _reports.log_export(db, ctx, report_id=body.report_id, format=body.format)
    return {"status": "logged"}


@router.get("/reports/summary", response_model=ReportsSummaryResponse)
def reports_summary(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ReportsSummaryResponse:
    require_module(ctx, "reports")
    return ReportsSummaryResponse(**_reports.summary(db))


@router.get("/settings/dashboard")
def settings_dashboard(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "settings")
    return _settings.dashboard(db, settings)


@router.get("/settings/center")
def settings_center(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "settings")
    return _settings.center(db, settings)


@router.get("/settings/health")
def settings_health(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "settings")
    return _settings.integration_health(db, settings)


@router.get("/settings/sections")
def settings_sections(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
):
    require_module(ctx, "settings")
    from porterchain_api.admin_engine.settings_service import SETTINGS_SECTIONS

    return SETTINGS_SECTIONS


@router.get("/settings/permissions")
def settings_permissions(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
):
    require_module(ctx, "settings")
    return _settings.permissions_matrix()


@router.get("/settings/rbac")
def settings_rbac(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
):
    require_module(ctx, "settings")
    from porterchain_api.auth.enterprise_rbac import rbac_matrix

    return rbac_matrix()


@router.get("/settings/audit")
def settings_audit(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    limit: int = Query(100, le=500),
):
    require_module(ctx, "settings")
    return _settings.audit_log(db, limit=limit)


@router.get("/settings/search")
def settings_search(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    q: str = "",
):
    require_module(ctx, "settings")
    return _settings.search(q)


@router.get("/settings/validate")
def settings_validate(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "settings")
    return _settings.validate(settings, db)


@router.get("/settings/export")
def settings_export(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.export_configuration(db)


@router.post("/settings/import")
def settings_import(
    body: SettingsImportRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.import_configuration(db, ctx, body.config, reason=body.reason)


@router.get("/settings/staff", response_model=list[StaffItem])
def list_staff(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[StaffItem]:
    require_module(ctx, "settings")
    return [
        StaffItem(id=u.id, email=u.email, name=u.name, role=u.role, created_at=u.created_at)
        for u in _settings.list_staff(db)
    ]


@router.get("/settings/users/{user_type}", response_model=PlatformUsersResponse)
def list_platform_users(
    user_type: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    limit: int = Query(500, ge=1, le=2000),
    search: str | None = Query(None, max_length=200),
    access_status: str | None = Query(None),
    invite_status: str | None = Query(None),
    identity_status: str | None = Query(None),
    account_status: str | None = Query(None),
    clerk_status: str | None = Query(None),
) -> PlatformUsersResponse:
    require_module(ctx, "settings")
    if user_type not in ("staff", "driver", "customer", "merchant"):
        raise HTTPException(400, "invalid_user_type")
    try:
        return _settings.list_platform_users(
            db,
            settings,
            user_type,
            limit=limit,
            search=search,
            access_status=access_status,
            invite_status=invite_status,
            identity_status=identity_status,
            account_status=account_status,
            clerk_status=clerk_status,
        )
    except ValueError as exc:
        raise HTTPException(400, "invalid_user_type") from exc


@router.post("/settings/users/{user_type}", status_code=201)
def create_platform_user(
    user_type: str,
    body: PlatformUserCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    require_module(ctx, "settings")
    if user_type not in ("staff", "driver", "customer", "merchant"):
        raise HTTPException(400, "invalid_user_type")
    try:
        return _clerk_directory.create_user(
            db,
            ctx,
            settings,
            user_type,
            email=body.email,
            name=body.name,
            role=body.role,
            password=body.password,
            send_invite=body.send_invite,
            merchant_id=body.merchant_id,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "clerk_not_configured":
            raise HTTPException(503, detail) from exc
        raise HTTPException(400, detail) from exc


@router.patch("/settings/users/{user_type}/clerk")
def update_platform_clerk_user(
    user_type: str,
    body: PlatformUserUpdateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    require_module(ctx, "settings")
    if user_type not in ("staff", "driver", "customer", "merchant"):
        raise HTTPException(400, "invalid_user_type")
    try:
        return _clerk_directory.update_clerk_user(
            db,
            ctx,
            settings,
            user_type,
            body.clerk_user_id,
            name=body.name,
            password=body.password,
            banned=body.banned,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/settings/users/{user_type}/delete", status_code=204)
def delete_platform_user(
    user_type: str,
    body: PlatformUserDeleteRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    require_module(ctx, "settings")
    if user_type not in ("staff", "driver", "customer", "merchant"):
        raise HTTPException(400, "invalid_user_type")
    if not body.clerk_user_id and not body.platform_user_id:
        raise HTTPException(400, "clerk_user_id_or_platform_user_id_required")
    try:
        _clerk_directory.delete_clerk_user(
            db,
            ctx,
            settings,
            user_type,
            clerk_user_id=body.clerk_user_id,
            platform_user_id=body.platform_user_id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/settings/staff/invite", response_model=StaffInviteResponse, status_code=201)
def invite_staff(
    body: StaffInviteRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> StaffInviteResponse:
    require_module(ctx, "settings")
    try:
        user, invitation = _settings.invite_staff(
            db, ctx, settings, email=body.email, role=body.role, name=body.name
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "clerk_not_configured":
            raise HTTPException(503, "clerk_not_configured") from exc
        if detail == "invalid_admin_role":
            raise HTTPException(400, "invalid_admin_role") from exc
        raise
    return StaffInviteResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        clerk_action=invitation.invitation_metadata.get("clerk_action", "invited"),
        invitation_status=invitation.status,
        created_at=user.created_at,
    )


@router.patch("/settings/staff/{user_id}/role", response_model=StaffItem)
def update_staff_role(
    user_id: str,
    body: StaffRoleUpdateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> StaffItem:
    require_module(ctx, "settings")
    try:
        u = _settings.update_staff_role(db, ctx, user_id, body.role, reason=body.reason)
    except LookupError:
        raise HTTPException(404, "staff_not_found") from None
    return StaffItem(id=u.id, email=u.email, name=u.name, role=u.role, created_at=u.created_at)


@router.get("/settings/vehicles/overview")
def settings_vehicles_overview(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.vehicles_overview(db)


@router.get("/settings/config")
def get_system_config(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return {
        "config": _settings.default_config(db),
        "module_config": _settings.module_config_links(db),
    }


@router.put("/settings/config/{key}")
def update_system_config(
    key: str,
    body: SettingsConfigUpdateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    from porterchain_api.admin_engine.settings_service import CONFIG_KEYS, DEFAULTS

    resolved = CONFIG_KEYS.get(key, key)
    if resolved not in DEFAULTS and not resolved.startswith("settings_"):
        raise HTTPException(400, "unknown_config_key")
    record = _settings.set_config(db, ctx, resolved, body.value, reason=body.reason)
    return {"key": record.key, "value": record.value}
