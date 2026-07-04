"""Merchant portal API — /v1/merchant/*"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from porterchain_api.auth.merchant import get_merchant_context
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.merchant_engine.api_key_service import MerchantApiKeyService
from porterchain_api.merchant_engine.billing_service import MerchantBillingService
from porterchain_api.merchant_engine.booking_flow_service import MerchantBookingFlowService
from porterchain_api.merchant_engine.booking_service import MerchantBookingService
from porterchain_api.merchant_engine.bulk_service import MerchantBulkService
from porterchain_api.merchant_engine.integrations_service import MerchantIntegrationsService
from porterchain_api.merchant_engine.dashboard_service import MerchantDashboardService
from porterchain_api.merchant_engine.orders_service import MerchantOrderFilters, MerchantOrdersService
from porterchain_api.merchant_engine.profile_service import MerchantProfileService
from porterchain_api.merchant_engine.rbac import MerchantContext, require_module
from porterchain_api.merchant_engine.reports_service import MerchantReportsService
from porterchain_api.merchant_engine.settings_service import MerchantSettingsService
from porterchain_api.merchant_engine.support_bridge_service import MerchantSupportBridgeService
from porterchain_api.merchant_engine.contacts_service import MerchantContactsService
from porterchain_api.merchant_engine.team_service import MerchantTeamService
from porterchain_api.merchant_engine.tracking_service import MerchantTrackingService
from porterchain_api.models import Order
from porterchain_api.schemas_admin import OrderListItem
from porterchain_api.schemas_merchant import (
    ApiKeyCreateRequest,
    ApiKeyResponse,
    BillingStatementResponse,
    BulkUploadResponse,
    BillingContactRequest,
    BusinessDocumentRequest,
    MerchantBrandingRequest,
    MerchantContactCreateRequest,
    MerchantContactResponse,
    MerchantContactUpdateRequest,
    MerchantClaimOpenRequest,
    MerchantNotificationsRequest,
    MerchantSupportTicketRequest,
    MerchantTwoFactorRequest,
    WarehouseRequest,
    InvoiceListItem,
    MerchantBookDeliveryRequest,
    MerchantBookingConfirmRequest,
    MerchantBookingConfirmResponse,
    MerchantBookingDraftResponse,
    MerchantBookingPreviewResponse,
    MerchantBookingTemplateCreateRequest,
    MerchantBookingTemplateResponse,
    MerchantConsoleRequest,
    MerchantApiKeyRateLimitRequest,
    MerchantSandboxRequest,
    MerchantLiveTrackingResponse,
    MerchantMultiParcelRequest,
    MerchantMultiParcelResponse,
    MerchantTrackingDashboardResponse,
    MerchantBillingOverviewResponse,
    MerchantBillingHistoryItem,
    MerchantContractPricingResponse,
    MerchantCreditNoteItem,
    MerchantDashboardResponse,
    MerchantPaymentItem,
    MerchantStatementDetailResponse,
    MerchantTaxSummaryResponse,
    MerchantOrderBulkRequest,
    MerchantOrderResponse,
    MerchantOrder360Response,
    MerchantOrdersDashboardResponse,
    MerchantProfileResponse,
    MerchantProfileUpdateRequest,
    OrderTrackingResponse,
    RecipientCreateRequest,
    RecipientResponse,
    MerchantReportSaveRequest,
    MerchantReportScheduleRequest,
    ReportSummaryResponse,
    SavedAddressCreateRequest,
    SavedAddressResponse,
    TeamInviteRequest,
    TeamMemberResponse,
    TeamRoleUpdateRequest,
    WebhookCreateRequest,
    WebhookResponse,
    WebhookUpdateRequest,
)

router = APIRouter(prefix="/v1/merchant", tags=["merchant"])

_dashboard = MerchantDashboardService()
_booking = MerchantBookingService()
_booking_flow = MerchantBookingFlowService()
_bulk = MerchantBulkService()
_orders = MerchantOrdersService()
_tracking = MerchantTrackingService()
_billing = MerchantBillingService()
_profile = MerchantProfileService()
_team = MerchantTeamService()
_contacts = MerchantContactsService()
_settings = MerchantSettingsService()
_support = MerchantSupportBridgeService()
_api_keys = MerchantApiKeyService()
_integrations = MerchantIntegrationsService()
_reports = MerchantReportsService()


def _order_response(order: Order) -> MerchantOrderResponse:
    return MerchantOrderResponse(
        order_id=order.id,
        order_number=order.order_number,
        tracking_number=order.tracking_number,
        state=order.state,
        amount_cents=order.amount_cents,
        currency=order.currency,
        scheduled_at=order.scheduled_at,
        pickup=order.pickup,
        dropoff=order.dropoff,
        internal_reference=order.internal_reference,
        purchase_order_number=order.purchase_order_number,
        fleetbase_order_id=order.fleetbase_order_id,
        created_at=order.created_at,
    )


def _profile_response(merchant) -> MerchantProfileResponse:
    return MerchantProfileResponse(
        id=merchant.id,
        status=merchant.status,
        company_name=merchant.company_name,
        legal_name=merchant.legal_name,
        email=merchant.email,
        phone=merchant.phone,
        payment_terms=merchant.payment_terms,
        hst_number=merchant.hst_number,
        business_number=merchant.business_number,
        billing_address=merchant.billing_address,
        preferred_vehicles=merchant.preferred_vehicles,
        delivery_zones=merchant.delivery_zones,
    )


def _handle_permission(exc: PermissionError) -> None:
    raise HTTPException(status_code=403, detail=str(exc)) from exc


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


@router.get("/orders/dashboard", response_model=MerchantOrdersDashboardResponse)
def merchant_orders_dashboard(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantOrdersDashboardResponse:
    require_module(ctx, "orders")
    return MerchantOrdersDashboardResponse(**_orders.orders_dashboard(db, ctx))


@router.get("/orders", response_model=list[OrderListItem])
def list_orders(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    state: str | None = None,
    payment_status: str | None = None,
    invoice_status: str | None = None,
    driver_id: str | None = None,
    priority: str | None = None,
    service_type: str | None = None,
    city: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    amount_min_cents: int | None = None,
    amount_max_cents: int | None = None,
    limit: int = Query(500, le=500),
    offset: int = Query(0, ge=0),
) -> list[OrderListItem]:
    from datetime import datetime

    require_module(ctx, "orders")
    filters = MerchantOrderFilters(
        state=state,
        payment_status=payment_status,
        invoice_status=invoice_status,
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
    return [OrderListItem(**row) for row in _orders.list_enriched(db, ctx, filters)]


@router.post("/orders/bulk")
def merchant_orders_bulk(
    body: MerchantOrderBulkRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    require_module(ctx, "orders_write")
    results = _orders.bulk_action(db, settings, ctx, body.order_ids, body.action)
    return {"results": results}


@router.get("/orders/{order_id}", response_model=MerchantOrderResponse)
def get_order(
    order_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantOrderResponse:
    require_module(ctx, "orders")
    order = _orders.get_order(db, ctx, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")
    return _order_response(order)


@router.get("/orders/{order_id}/360", response_model=MerchantOrder360Response)
def merchant_order_360(
    order_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MerchantOrder360Response:
    require_module(ctx, "orders")
    try:
        detail = _orders.get_detail_360(db, settings, ctx, order_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="order_not_found") from None
    return MerchantOrder360Response(**detail)


@router.get("/orders/{order_id}/tracking", response_model=MerchantLiveTrackingResponse)
def merchant_order_tracking(
    order_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MerchantLiveTrackingResponse:
    require_module(ctx, "tracking")
    try:
        return MerchantLiveTrackingResponse(**_tracking.live_tracking(db, settings, ctx, order_id))
    except LookupError:
        raise HTTPException(status_code=404, detail="order_not_found") from None


@router.get("/tracking/dashboard", response_model=MerchantTrackingDashboardResponse)
def merchant_tracking_dashboard(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MerchantTrackingDashboardResponse:
    require_module(ctx, "tracking")
    return MerchantTrackingDashboardResponse(**_tracking.dashboard(db, settings, ctx))


@router.get("/tracking/orders/{order_id}", response_model=MerchantLiveTrackingResponse)
def merchant_tracking_detail(
    order_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MerchantLiveTrackingResponse:
    require_module(ctx, "tracking")
    try:
        return MerchantLiveTrackingResponse(**_tracking.live_tracking(db, settings, ctx, order_id))
    except LookupError:
        raise HTTPException(status_code=404, detail="order_not_found") from None


@router.get("/track/{tracking_number}", response_model=OrderTrackingResponse)
def track_by_number(
    tracking_number: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OrderTrackingResponse:
    require_module(ctx, "tracking")
    try:
        live = _tracking.track_by_number(db, settings, ctx, tracking_number)
        order = _orders.get_by_tracking(db, ctx, tracking_number)
        if not order:
            raise HTTPException(status_code=404, detail="order_not_found")
        timeline = live.get("timeline") or live.get("tracking_history") or []
        return OrderTrackingResponse(
            order=_order_response(order),
            timeline=timeline,
            live_tracking=live,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="order_not_found") from None


@router.post("/orders/{order_id}/cancel", response_model=MerchantOrderResponse)
def cancel_order(
    order_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MerchantOrderResponse:
    try:
        require_module(ctx, "orders_write")
        order = _orders.get_order(db, ctx, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="order_not_found")
        order = _booking.cancel_order(db, ctx, order, settings)
        return _order_response(order)
    except PermissionError as exc:
        _handle_permission(exc)


@router.post("/orders/{order_id}/duplicate", response_model=MerchantOrderResponse)
def duplicate_order(
    order_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MerchantOrderResponse:
    try:
        require_module(ctx, "orders_write")
        order = _orders.get_order(db, ctx, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="order_not_found")
        new_order = _booking.duplicate_order(db, settings, ctx, order)
        return _order_response(new_order)
    except PermissionError as exc:
        _handle_permission(exc)


@router.get("/billing/overview", response_model=MerchantBillingOverviewResponse)
def billing_overview(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantBillingOverviewResponse:
    require_module(ctx, "billing")
    data = _billing.overview(db, ctx)
    return MerchantBillingOverviewResponse(
        **{k: v for k, v in data.items() if k not in ("tax_summary", "contract_pricing")},
        tax_summary=MerchantTaxSummaryResponse(**data["tax_summary"]),
        contract_pricing=MerchantContractPricingResponse(**data["contract_pricing"]),
    )


@router.get("/billing/statement", response_model=BillingStatementResponse)
def billing_statement(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> BillingStatementResponse:
    require_module(ctx, "billing")
    return BillingStatementResponse(**_billing.statement_summary(db, ctx))


@router.get("/billing/statement/detail", response_model=MerchantStatementDetailResponse)
def billing_statement_detail(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantStatementDetailResponse:
    require_module(ctx, "statements")
    return MerchantStatementDetailResponse(**_billing.statement_detail(db, ctx))


@router.get("/billing/invoices", response_model=list[InvoiceListItem])
def list_invoices(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[InvoiceListItem]:
    require_module(ctx, "invoices")
    rows = _billing.list_invoices_enriched(db, ctx)
    return [InvoiceListItem(**r) for r in rows]


@router.get("/billing/invoices/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "invoices")
    try:
        url = _billing.get_invoice_pdf_url(db, ctx, invoice_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="invoice_not_found") from None
    if not url:
        raise HTTPException(status_code=404, detail="pdf_not_available")
    return RedirectResponse(url=url)


@router.get("/billing/payments", response_model=list[MerchantPaymentItem])
def list_billing_payments(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[MerchantPaymentItem]:
    require_module(ctx, "billing")
    return [MerchantPaymentItem(**r) for r in _billing.list_payments(db, ctx)]


@router.get("/billing/credit-notes", response_model=list[MerchantCreditNoteItem])
def list_credit_notes(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[MerchantCreditNoteItem]:
    require_module(ctx, "billing")
    return [MerchantCreditNoteItem(**r) for r in _billing.list_credit_notes(db, ctx)]


@router.get("/billing/history", response_model=list[MerchantBillingHistoryItem])
def billing_history(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[MerchantBillingHistoryItem]:
    require_module(ctx, "billing")
    return [MerchantBillingHistoryItem(**r) for r in _billing.billing_history(db, ctx)]


@router.get("/billing/tax-summary", response_model=MerchantTaxSummaryResponse)
def billing_tax_summary(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantTaxSummaryResponse:
    require_module(ctx, "billing")
    return MerchantTaxSummaryResponse(**_billing.tax_summary(db, ctx))


@router.get("/billing/contract", response_model=MerchantContractPricingResponse)
def billing_contract(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantContractPricingResponse:
    require_module(ctx, "billing")
    return MerchantContractPricingResponse(**_billing.contract_pricing(db, ctx))


@router.get("/billing/export/invoices.csv")
def export_invoices_csv(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> Response:
    require_module(ctx, "invoices")
    content = _billing.export_invoices_csv(db, ctx)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=merchant-invoices.csv"},
    )


@router.get("/billing/export/statement.csv")
def export_statement_csv(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> Response:
    require_module(ctx, "statements")
    content = _billing.export_statement_csv(db, ctx)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=merchant-statement.csv"},
    )


@router.get("/billing/export/history.csv")
def export_history_csv(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> Response:
    require_module(ctx, "billing")
    content = _billing.export_history_csv(db, ctx)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=merchant-billing-history.csv"},
    )


@router.get("/reports/summary", response_model=ReportSummaryResponse)
def reports_summary(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> ReportSummaryResponse:
    require_module(ctx, "reports")
    return ReportSummaryResponse(**_reports.summary(db, ctx))


@router.get("/reports/overview")
def reports_overview(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.overview(db, ctx)


@router.get("/reports/executive")
def reports_executive(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.executive(db, ctx)


@router.get("/reports/delivery-performance")
def reports_delivery_performance(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.delivery_performance(db, ctx)


@router.get("/reports/order-volume")
def reports_order_volume(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.order_volume(db, ctx)


@router.get("/reports/invoices")
def reports_invoices(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.invoice_reports(db, ctx)


@router.get("/reports/drivers")
def reports_drivers(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.driver_reports(db, ctx)


@router.get("/reports/vehicles")
def reports_vehicles(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.vehicle_reports(db, ctx)


@router.get("/reports/destinations")
def reports_destinations(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.destination_reports(db, ctx)


@router.get("/reports/claims")
def reports_claims(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.claims_reports(db, ctx)


@router.get("/reports/saved")
def reports_saved_list(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "reports")
    return _reports.list_saved_reports(ctx)


@router.post("/reports/saved")
def reports_saved_create(
    body: MerchantReportSaveRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.save_report(
        db,
        ctx,
        name=body.name,
        report_type=body.report_type,
        chart_type=body.chart_type,
        filters=body.filters,
    )


@router.delete("/reports/saved/{report_id}")
def reports_saved_delete(
    report_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    _reports.delete_saved_report(db, ctx, report_id)
    return {"ok": True}


@router.get("/reports/scheduled")
def reports_scheduled_list(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "reports")
    return _reports.list_scheduled_reports(ctx)


@router.post("/reports/scheduled")
def reports_scheduled_create(
    body: MerchantReportScheduleRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    return _reports.save_scheduled_report(
        db,
        ctx,
        name=body.name,
        report_type=body.report_type,
        schedule=body.schedule,
        email=body.email,
    )


@router.get("/reports/export/{report_type}.csv")
def reports_export_csv(
    report_type: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    content = _reports.export_csv(db, ctx, report_type)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=merchant-{report_type}-report.csv"},
    )


@router.get("/reports/export/{report_type}.xlsx")
def reports_export_excel(
    report_type: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "reports")
    try:
        content = _reports.export_excel(db, ctx, report_type)
    except ValueError as exc:
        if str(exc) == "excel_support_unavailable":
            raise HTTPException(status_code=503, detail="excel_export_unavailable") from exc
        raise
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=merchant-{report_type}-report.xlsx"},
    )


@router.get("/profile", response_model=MerchantProfileResponse)
def get_profile(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
) -> MerchantProfileResponse:
    require_module(ctx, "settings")
    return _profile_response(_profile.get_profile(ctx))


@router.patch("/profile", response_model=MerchantProfileResponse)
def update_profile(
    body: MerchantProfileUpdateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantProfileResponse:
    require_module(ctx, "settings")
    merchant = _profile.update_profile(db, ctx, body)
    return _profile_response(merchant)


@router.get("/addresses", response_model=list[SavedAddressResponse])
def list_addresses(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[SavedAddressResponse]:
    require_module(ctx, "settings")
    rows = _profile.list_saved_addresses(db, ctx)
    return [
        SavedAddressResponse(
            id=r.id, label=r.label, address_type=r.address_type, formatted=r.formatted, is_default=r.is_default
        )
        for r in rows
    ]


@router.post("/addresses", response_model=SavedAddressResponse)
def create_address(
    body: SavedAddressCreateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> SavedAddressResponse:
    require_module(ctx, "settings")
    r = _profile.create_saved_address(db, ctx, **body.model_dump())
    return SavedAddressResponse(
        id=r.id, label=r.label, address_type=r.address_type, formatted=r.formatted, is_default=r.is_default
    )


@router.get("/recipients", response_model=list[RecipientResponse])
def list_recipients(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[RecipientResponse]:
    require_module(ctx, "settings")
    rows = _profile.list_recipients(db, ctx)
    return [
        RecipientResponse(id=r.id, name=r.name, email=r.email, phone=r.phone, company=r.company) for r in rows
    ]


@router.post("/recipients", response_model=RecipientResponse)
def create_recipient(
    body: RecipientCreateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> RecipientResponse:
    require_module(ctx, "settings")
    r = _profile.create_recipient(db, ctx, **body.model_dump())
    return RecipientResponse(id=r.id, name=r.name, email=r.email, phone=r.phone, company=r.company)


@router.get("/contacts", response_model=list[MerchantContactResponse])
def list_contacts(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[MerchantContactResponse]:
    require_module(ctx, "users")
    return [MerchantContactResponse(**row) for row in _contacts.list_contacts(db, ctx)]


@router.post("/contacts", response_model=MerchantContactResponse, status_code=201)
def create_contact(
    body: MerchantContactCreateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantContactResponse:
    require_module(ctx, "users")
    try:
        row = _contacts.create_contact(db, ctx, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MerchantContactResponse(**row)


@router.patch("/contacts/{contact_id}", response_model=MerchantContactResponse)
def update_contact(
    contact_id: str,
    body: MerchantContactUpdateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantContactResponse:
    require_module(ctx, "users")
    try:
        row = _contacts.update_contact(
            db, ctx, contact_id, body.model_dump(exclude_unset=True)
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="contact_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MerchantContactResponse(**row)


@router.delete("/contacts/{contact_id}", status_code=204)
def delete_contact(
    contact_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> None:
    require_module(ctx, "users")
    try:
        _contacts.delete_contact(db, ctx, contact_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="contact_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/team/overview")
def team_overview(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "users")
    return _team.overview(db, ctx)


@router.get("/team/activity")
def team_activity(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200),
):
    require_module(ctx, "users")
    return _team.activity_log(db, ctx, limit=limit)


@router.get("/team/roles")
def team_roles(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "users")
    return _team.roles_and_permissions()


@router.get("/team/two-factor")
def team_two_factor_get(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "users")
    return _team.two_factor_status(ctx)


@router.patch("/team/two-factor")
def team_two_factor_patch(
    body: MerchantTwoFactorRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "users")
    return _team.update_two_factor(db, ctx, enabled=body.enabled, method=body.method)


@router.get("/team", response_model=list[TeamMemberResponse])
def list_team(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[TeamMemberResponse]:
    require_module(ctx, "users")
    members = _team.list_members(db, ctx)
    return [
        TeamMemberResponse(id=m.id, email=m.email, role=m.role, is_active=m.is_active, created_at=m.created_at)
        for m in members
    ]


@router.post("/team/invite", response_model=TeamMemberResponse)
def invite_team_member(
    body: TeamInviteRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TeamMemberResponse:
    require_module(ctx, "users")
    try:
        m = _team.invite_member(db, ctx, settings, email=body.email, role=body.role)
    except ValueError as exc:
        if str(exc) == "clerk_not_configured":
            raise HTTPException(status_code=503, detail="clerk_not_configured") from exc
        raise
    _contacts.sync_team_contacts(db, ctx.merchant)
    return TeamMemberResponse(id=m.id, email=m.email, role=m.role, is_active=m.is_active, created_at=m.created_at)


@router.delete("/team/{user_id}", status_code=204)
def remove_team_member(
    user_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> None:
    require_module(ctx, "users")
    try:
        _team.remove_member(db, ctx, user_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="team_member_not_found") from None
    except PermissionError as exc:
        _handle_permission(exc)
    _contacts.sync_team_contacts(db, ctx.merchant)


@router.patch("/team/{user_id}/role", response_model=TeamMemberResponse)
def update_team_role(
    user_id: str,
    body: TeamRoleUpdateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> TeamMemberResponse:
    require_module(ctx, "users")
    try:
        m = _team.update_role(db, ctx, user_id, body.role)
        _contacts.sync_team_contacts(db, ctx.merchant)
        return TeamMemberResponse(id=m.id, email=m.email, role=m.role, is_active=m.is_active, created_at=m.created_at)
    except LookupError:
        raise HTTPException(status_code=404, detail="team_member_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/settings/overview")
def settings_overview(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.overview(db, ctx)


@router.patch("/settings/notifications")
def settings_notifications(
    body: MerchantNotificationsRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.update_notifications(db, ctx, body.model_dump(exclude_none=True))


@router.patch("/settings/branding")
def settings_branding(
    body: MerchantBrandingRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.update_branding(db, ctx, body.model_dump(exclude_none=True))


@router.get("/settings/billing-contacts")
def settings_billing_contacts_list(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "settings")
    return _settings.list_billing_contacts(ctx)


@router.post("/settings/billing-contacts")
def settings_billing_contacts_create(
    body: BillingContactRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.save_billing_contact(db, ctx, **body.model_dump())


@router.delete("/settings/billing-contacts/{contact_id}", status_code=204)
def settings_billing_contacts_delete(
    contact_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> None:
    require_module(ctx, "settings")
    _settings.delete_billing_contact(db, ctx, contact_id)


@router.get("/settings/warehouses")
def settings_warehouses_list(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "settings")
    return _settings.list_warehouses(ctx)


@router.post("/settings/warehouses")
def settings_warehouses_create(
    body: WarehouseRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.save_warehouse(db, ctx, **body.model_dump())


@router.patch("/settings/warehouses/{warehouse_id}")
def settings_warehouses_update(
    warehouse_id: str,
    body: WarehouseRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.save_warehouse(db, ctx, warehouse_id=warehouse_id, **body.model_dump())


@router.delete("/settings/warehouses/{warehouse_id}", status_code=204)
def settings_warehouses_delete(
    warehouse_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> None:
    require_module(ctx, "settings")
    _settings.delete_warehouse(db, ctx, warehouse_id)


@router.get("/settings/documents")
def settings_documents_list(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "settings")
    return _settings.list_documents(ctx)


@router.post("/settings/documents")
def settings_documents_create(
    body: BusinessDocumentRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.add_document(db, ctx, name=body.name, doc_type=body.doc_type, reference=body.reference)


@router.delete("/settings/documents/{doc_id}", status_code=204)
def settings_documents_delete(
    doc_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> None:
    require_module(ctx, "settings")
    _settings.delete_document(db, ctx, doc_id)


@router.get("/settings/tax")
def settings_tax_get(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "settings")
    return _settings.tax_info(ctx)


@router.patch("/settings/tax")
def settings_tax_patch(
    body: MerchantProfileUpdateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.update_tax(db, ctx, body)


@router.get("/settings/contract")
def settings_contract(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.contract_summary(db, ctx)


@router.delete("/addresses/{address_id}", status_code=204)
def delete_address(
    address_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> None:
    require_module(ctx, "settings")
    try:
        _profile.delete_saved_address(db, ctx, address_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="address_not_found") from None


@router.get("/support/tickets")
def support_tickets_list(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    limit: int = Query(50, le=100),
):
    require_module(ctx, "support")
    return _support.list_tickets(db, ctx, limit=limit)


@router.get("/support/tickets/{ticket_id}")
def support_ticket_detail(
    ticket_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support")
    try:
        return _support.get_ticket(db, ctx, ticket_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="ticket_not_found") from None


@router.post("/support/tickets")
def support_ticket_create(
    body: MerchantSupportTicketRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support")
    try:
        return _support.create_ticket(db, ctx, **body.model_dump())
    except LookupError:
        raise HTTPException(status_code=404, detail="order_not_found") from None


@router.get("/support/knowledge-base")
def support_knowledge_base(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support")
    return _support.knowledge_base(db)


@router.get("/claims")
def merchant_claims_list(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    limit: int = Query(50, le=100),
):
    require_module(ctx, "claims")
    return _support.list_claims(db, ctx, limit=limit)


@router.get("/claims/{claim_id}")
def merchant_claim_detail(
    claim_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "claims")
    try:
        return _support.get_claim(db, ctx, claim_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="claim_not_found") from None


@router.post("/claims")
def merchant_claim_open(
    body: MerchantClaimOpenRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "claims")
    try:
        return _support.open_claim(db, ctx, **body.model_dump())
    except LookupError:
        raise HTTPException(status_code=404, detail="order_not_found") from None


@router.get("/api-keys", response_model=list[ApiKeyResponse])
def list_api_keys(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[ApiKeyResponse]:
    require_module(ctx, "api_keys")
    keys = _api_keys.list_keys(db, ctx)
    return [
        ApiKeyResponse(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            scopes=k.scopes,
            environment=k.environment,
            rate_limit_per_minute=k.rate_limit_per_minute,
            is_active=k.is_active,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.post("/api-keys", response_model=ApiKeyResponse)
def create_api_key(
    body: ApiKeyCreateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> ApiKeyResponse:
    require_module(ctx, "api_keys")
    record, secret = _api_keys.create_key(
        db, ctx, name=body.name, scopes=body.scopes, environment=body.environment
    )
    return ApiKeyResponse(
        id=record.id,
        name=record.name,
        key_prefix=record.key_prefix,
        scopes=record.scopes,
        environment=record.environment,
        rate_limit_per_minute=record.rate_limit_per_minute,
        is_active=record.is_active,
        created_at=record.created_at,
        secret=secret,
    )


@router.delete("/api-keys/{key_id}", status_code=204)
def revoke_api_key(
    key_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> None:
    require_module(ctx, "api_keys")
    try:
        _api_keys.revoke_key(db, ctx, key_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="api_key_not_found") from None


@router.get("/webhooks", response_model=list[WebhookResponse])
def list_webhooks(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[WebhookResponse]:
    require_module(ctx, "api_keys")
    hooks = _api_keys.list_webhooks(db, ctx)
    return [
        WebhookResponse(
            id=h.id,
            url=h.url,
            events=h.events,
            is_active=h.is_active,
            created_at=h.created_at,
        )
        for h in hooks
    ]


@router.post("/webhooks", response_model=WebhookResponse)
def create_webhook(
    body: WebhookCreateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> WebhookResponse:
    require_module(ctx, "api_keys")
    record, secret = _api_keys.create_webhook(
        db, ctx, url=body.url, events=body.events, encryption_key=settings.jwt_secret
    )
    return WebhookResponse(
        id=record.id,
        url=record.url,
        events=record.events,
        is_active=record.is_active,
        created_at=record.created_at,
        signing_secret=secret,
    )


@router.get("/integrations/overview")
def integrations_overview(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "api_keys")
    return _integrations.overview(db, ctx, api_base_url=settings.porterchain_api_url)


@router.get("/integrations/documentation")
def integrations_documentation(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "api_keys")
    return _integrations.documentation(api_base_url=settings.porterchain_api_url)


@router.get("/integrations/events")
def integrations_events(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "api_keys")
    return _integrations.event_catalog()


@router.get("/integrations/usage")
def integrations_usage(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    days: int = Query(7, ge=1, le=90),
):
    require_module(ctx, "api_keys")
    return _integrations.usage(db, ctx, days=days)


@router.get("/integrations/rate-limits")
def integrations_rate_limits(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "api_keys")
    return _integrations.rate_limits(db, ctx)


@router.get("/integrations/sandbox")
def integrations_sandbox_get(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "api_keys")
    return _integrations.sandbox_status(ctx)


@router.patch("/integrations/sandbox")
def integrations_sandbox_patch(
    body: MerchantSandboxRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "api_keys")
    return _integrations.set_sandbox_mode(db, ctx, body.sandbox_mode)


@router.get("/integrations/webhooks/logs")
def integrations_webhook_logs(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    webhook_id: str | None = None,
    limit: int = Query(50, le=200),
):
    require_module(ctx, "api_keys")
    return _integrations.webhook_logs(db, ctx, webhook_id=webhook_id, limit=limit)


@router.get("/integrations/webhooks/{webhook_id}/history")
def integrations_webhook_history(
    webhook_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "api_keys")
    try:
        return _integrations.webhook_history(db, ctx, webhook_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="webhook_not_found") from None


@router.post("/integrations/webhooks/{webhook_id}/test")
def integrations_webhook_test(
    webhook_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "api_keys")
    try:
        return _integrations.test_webhook(db, ctx, webhook_id, encryption_key=settings.jwt_secret)
    except LookupError:
        raise HTTPException(status_code=404, detail="webhook_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/integrations/webhooks/deliveries/{delivery_id}/retry")
def integrations_webhook_retry(
    delivery_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "api_keys")
    try:
        return _integrations.retry_delivery(db, ctx, delivery_id, encryption_key=settings.jwt_secret)
    except LookupError:
        raise HTTPException(status_code=404, detail="delivery_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/integrations/webhooks/{webhook_id}", response_model=WebhookResponse)
def integrations_webhook_update(
    webhook_id: str,
    body: WebhookUpdateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> WebhookResponse:
    require_module(ctx, "api_keys")
    try:
        hook = _integrations.update_webhook(
            db,
            ctx,
            webhook_id,
            url=body.url,
            events=body.events,
            is_active=body.is_active,
        )
        return WebhookResponse(
            id=hook.id,
            url=hook.url,
            events=hook.events,
            is_active=hook.is_active,
            created_at=hook.created_at,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="webhook_not_found") from None


@router.delete("/integrations/webhooks/{webhook_id}", status_code=204)
def integrations_webhook_delete(
    webhook_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> None:
    require_module(ctx, "api_keys")
    try:
        _integrations.delete_webhook(db, ctx, webhook_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="webhook_not_found") from None


@router.post("/integrations/webhooks/{webhook_id}/rotate-secret", response_model=WebhookResponse)
def integrations_webhook_rotate(
    webhook_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> WebhookResponse:
    require_module(ctx, "api_keys")
    try:
        hook, secret = _integrations.rotate_webhook_secret(
            db, ctx, webhook_id, encryption_key=settings.jwt_secret
        )
        return WebhookResponse(
            id=hook.id,
            url=hook.url,
            events=hook.events,
            is_active=hook.is_active,
            created_at=hook.created_at,
            signing_secret=secret,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="webhook_not_found") from None


@router.patch("/integrations/api-keys/{key_id}/rate-limit")
def integrations_api_key_rate_limit(
    key_id: str,
    body: MerchantApiKeyRateLimitRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "api_keys")
    try:
        return _integrations.update_api_key_rate_limit(
            db, ctx, key_id, rate_limit_per_minute=body.rate_limit_per_minute
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="api_key_not_found") from None


@router.get("/integrations/erp")
def integrations_erp(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "api_keys")
    return _integrations.erp_readiness()


@router.get("/integrations/oauth")
def integrations_oauth(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "api_keys")
    return _integrations.oauth_readiness()


@router.get("/integrations/csv-templates")
def integrations_csv_templates(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "api_keys")
    return _integrations.csv_templates()


@router.get("/integrations/csv-templates/{template_id}.csv")
def integrations_csv_template_download(
    template_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "api_keys")
    try:
        content = _integrations.csv_template_download(template_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="template_not_found") from None
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={template_id}-template.csv"},
    )


@router.post("/integrations/console")
def integrations_console(
    body: MerchantConsoleRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "api_keys")
    try:
        return _integrations.console_execute(db, settings, ctx, action=body.action, payload=body.payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
