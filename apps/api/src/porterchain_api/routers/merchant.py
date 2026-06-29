"""Merchant portal API — /v1/merchant/*"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from porterchain_api.auth.merchant import get_merchant_context
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.merchant_engine.api_key_service import MerchantApiKeyService
from porterchain_api.merchant_engine.billing_service import MerchantBillingService
from porterchain_api.merchant_engine.booking_service import MerchantBookingService
from porterchain_api.merchant_engine.bulk_service import MerchantBulkService
from porterchain_api.merchant_engine.dashboard_service import MerchantDashboardService
from porterchain_api.merchant_engine.orders_service import MerchantOrdersService
from porterchain_api.merchant_engine.profile_service import MerchantProfileService
from porterchain_api.merchant_engine.rbac import MerchantContext, require_module
from porterchain_api.merchant_engine.reports_service import MerchantReportsService
from porterchain_api.merchant_engine.team_service import MerchantTeamService
from porterchain_api.models import Order
from porterchain_api.schemas_merchant import (
    ApiKeyCreateRequest,
    ApiKeyResponse,
    BillingStatementResponse,
    BulkUploadResponse,
    InvoiceListItem,
    MerchantBookDeliveryRequest,
    MerchantDashboardResponse,
    MerchantOrderResponse,
    MerchantProfileResponse,
    MerchantProfileUpdateRequest,
    OrderTrackingResponse,
    RecipientCreateRequest,
    RecipientResponse,
    ReportSummaryResponse,
    SavedAddressCreateRequest,
    SavedAddressResponse,
    TeamInviteRequest,
    TeamMemberResponse,
    TeamRoleUpdateRequest,
    WebhookCreateRequest,
    WebhookResponse,
)

router = APIRouter(prefix="/v1/merchant", tags=["merchant"])

_dashboard = MerchantDashboardService()
_booking = MerchantBookingService()
_bulk = MerchantBulkService()
_orders = MerchantOrdersService()
_billing = MerchantBillingService()
_profile = MerchantProfileService()
_team = MerchantTeamService()
_api_keys = MerchantApiKeyService()
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


@router.post("/bulk/upload", response_model=BulkUploadResponse)
async def bulk_upload(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
) -> BulkUploadResponse:
    try:
        require_module(ctx, "bulk")
        content = (await file.read()).decode("utf-8", errors="replace")
        job = _bulk.upload_csv(db, ctx, filename=file.filename or "upload.csv", content=content)
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


@router.get("/orders", response_model=list[MerchantOrderResponse])
def list_orders(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    state: str | None = None,
    search: str | None = None,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
) -> list[MerchantOrderResponse]:
    require_module(ctx, "orders")
    orders = _orders.list_orders(db, ctx, state=state, search=search, limit=limit, offset=offset)
    return [_order_response(o) for o in orders]


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


@router.get("/orders/{order_id}/tracking", response_model=OrderTrackingResponse)
def order_tracking(
    order_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> OrderTrackingResponse:
    require_module(ctx, "tracking")
    order = _orders.get_order(db, ctx, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")
    timeline = _orders.get_tracking_timeline(db, ctx, order_id)
    return OrderTrackingResponse(order=_order_response(order), timeline=timeline)


@router.get("/track/{tracking_number}", response_model=OrderTrackingResponse)
def track_by_number(
    tracking_number: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> OrderTrackingResponse:
    require_module(ctx, "tracking")
    order = _orders.get_by_tracking(db, ctx, tracking_number)
    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")
    timeline = _orders.get_tracking_timeline(db, ctx, order.id)
    return OrderTrackingResponse(order=_order_response(order), timeline=timeline)


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


@router.get("/billing/statement", response_model=BillingStatementResponse)
def billing_statement(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> BillingStatementResponse:
    require_module(ctx, "billing")
    return BillingStatementResponse(**_billing.statement_summary(db, ctx))


@router.get("/billing/invoices", response_model=list[InvoiceListItem])
def list_invoices(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[InvoiceListItem]:
    require_module(ctx, "invoices")
    rows = _billing.list_invoices(db, ctx)
    return [InvoiceListItem(**r) for r in rows]


@router.get("/reports/summary", response_model=ReportSummaryResponse)
def reports_summary(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> ReportSummaryResponse:
    require_module(ctx, "reports")
    return ReportSummaryResponse(**_reports.summary(db, ctx))


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
) -> TeamMemberResponse:
    require_module(ctx, "users")
    m = _team.invite_member(db, ctx, email=body.email, role=body.role)
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
        return TeamMemberResponse(id=m.id, email=m.email, role=m.role, is_active=m.is_active, created_at=m.created_at)
    except LookupError:
        raise HTTPException(status_code=404, detail="team_member_not_found") from None


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
    return [WebhookResponse(id=h.id, url=h.url, events=h.events, is_active=h.is_active) for h in hooks]


@router.post("/webhooks", response_model=WebhookResponse)
def create_webhook(
    body: WebhookCreateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> WebhookResponse:
    require_module(ctx, "api_keys")
    record, _secret = _api_keys.create_webhook(db, ctx, url=body.url, events=body.events)
    return WebhookResponse(id=record.id, url=record.url, events=record.events, is_active=record.is_active)
