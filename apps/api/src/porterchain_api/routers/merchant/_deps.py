"""Merchant portal API — /v1/merchant/*"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from porterchain_api.auth.merchant import (
    MerchantSeats,
    get_merchant_context,
    get_merchant_seats,
)
from porterchain_api.booking_models import Order
from porterchain_api.compliance_engine.privacy_service import PrivacyService
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.merchant_engine.api_key_service import MerchantApiKeyService
from porterchain_api.merchant_engine.billing_service import MerchantBillingService
from porterchain_api.merchant_engine.booking_flow_service import (
    MerchantBookingFlowService,
)
from porterchain_api.merchant_engine.booking_service import MerchantBookingService
from porterchain_api.merchant_engine.bulk_service import MerchantBulkService
from porterchain_api.merchant_engine.contacts_service import MerchantContactsService
from porterchain_api.merchant_engine.dashboard_service import MerchantDashboardService
from porterchain_api.merchant_engine.integrations_service import (
    MerchantIntegrationsService,
)
from porterchain_api.merchant_engine.orders_service import (
    MerchantOrderFilters,
    MerchantOrdersService,
)
from porterchain_api.merchant_engine.profile_service import MerchantProfileService
from porterchain_api.merchant_engine.rbac import MerchantContext, forbidden_message
from porterchain_api.merchant_engine.rbac import require_module as _require_module
from porterchain_api.merchant_engine.reports_service import MerchantReportsService
from porterchain_api.merchant_engine.settings_service import MerchantSettingsService
from porterchain_api.merchant_engine.standing_order_service import (
    MerchantStandingOrderService,
)
from porterchain_api.merchant_engine.support_bridge_service import (
    MerchantSupportBridgeService,
)
from porterchain_api.merchant_engine.team_service import MerchantTeamService
from porterchain_api.merchant_engine.tracking_service import MerchantTrackingService
from porterchain_api.schemas_admin import OrderListItem, OrderListPage
from porterchain_api.schemas_merchant import (
    ApiKeyCreateRequest,
    ApiKeyResponse,
    BillingContactRequest,
    BillingStatementResponse,
    BulkUploadResponse,
    BusinessDocumentRequest,
    InvoiceDetailResponse,
    InvoiceListItem,
    MerchantApiKeyRateLimitRequest,
    MerchantBillingHistoryItem,
    MerchantBillingOverviewResponse,
    MerchantBookDeliveryRequest,
    MerchantBookingConfirmRequest,
    MerchantBookingConfirmResponse,
    MerchantBookingDraftResponse,
    MerchantBookingPreviewResponse,
    MerchantBookingTemplateCreateRequest,
    MerchantBookingTemplateResponse,
    MerchantBrandingRequest,
    MerchantClaimOpenRequest,
    MerchantConsoleRequest,
    MerchantContactCreateRequest,
    MerchantContactResponse,
    MerchantContactUpdateRequest,
    MerchantContractPricingResponse,
    MerchantCreditNoteItem,
    MerchantDashboardResponse,
    MerchantLiveTrackingResponse,
    MerchantMultiParcelRequest,
    MerchantMultiParcelResponse,
    MerchantNotificationsRequest,
    MerchantOrder360Response,
    MerchantOrderBulkRequest,
    MerchantOrderResponse,
    MerchantOrdersDashboardResponse,
    MerchantPaymentItem,
    MerchantProfileResponse,
    MerchantProfileUpdateRequest,
    MerchantRateCardResponse,
    MerchantReportSaveRequest,
    MerchantReportScheduleRequest,
    MerchantSandboxRequest,
    MerchantStandingOrderCreateRequest,
    MerchantStandingOrderResponse,
    MerchantStatementDetailResponse,
    MerchantSupportTicketRequest,
    MerchantTaxSummaryResponse,
    MerchantTrackingDashboardResponse,
    MerchantTrackingEmailRequest,
    MerchantTrackingEmailResponse,
    MerchantTwoFactorRequest,
    OrderTrackingResponse,
    RecipientCreateRequest,
    RecipientResponse,
    ReportSummaryResponse,
    SavedAddressCreateRequest,
    SavedAddressResponse,
    TeamInviteRequest,
    TeamMemberResponse,
    TeamMemberUpdateRequest,
    TeamRoleUpdateRequest,
    WarehouseRequest,
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
_privacy = PrivacyService()
_standing_orders = MerchantStandingOrderService()


def _order_response(order: Order) -> MerchantOrderResponse:
    meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
    is_sandbox = bool(getattr(order, "is_sandbox", False) or meta.get("sandbox") is True)
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
        cost_centre=order.cost_centre,
        is_sandbox=is_sandbox,
        created_at=order.created_at,
    )


def _profile_response(merchant, db=None) -> MerchantProfileResponse:
    from porterchain_api.merchant_engine.coverage import coverage_snapshot
    from porterchain_api.merchant_engine.profile_service import profile_public_fields

    extra = profile_public_fields(merchant)
    return MerchantProfileResponse(
        id=merchant.id,
        status=merchant.status,
        company_name=merchant.company_name,
        legal_name=merchant.legal_name,
        email=merchant.email,
        phone=merchant.phone,
        website=extra["website"],
        industry=extra["industry"],
        payment_terms=merchant.payment_terms,
        billing_cycle=merchant.billing_cycle,
        hst_number=merchant.hst_number,
        business_number=merchant.business_number,
        billing_address=merchant.billing_address,
        preferred_vehicles=merchant.preferred_vehicles,
        delivery_zones=merchant.delivery_zones,
        identity_meta=extra["identity_meta"],
        coverage=coverage_snapshot(merchant, db),
        cod_enabled=bool(getattr(merchant, "cod_enabled", False)),
        stripe_connect_account_id=getattr(merchant, "stripe_connect_account_id", None),
    )


def _recipient_out(row) -> RecipientResponse:
    return RecipientResponse(
        id=row.id,
        name=row.name,
        email=row.email,
        phone=row.phone,
        company=row.company,
        default_address=row.default_address,
    )


def _saved_address_out(row) -> SavedAddressResponse:
    return SavedAddressResponse(
        id=row.id,
        label=row.label,
        address_type=row.address_type,
        formatted=row.formatted,
        is_default=row.is_default,
        postal=getattr(row, "postal", None),
        lat=row.lat,
        lng=row.lng,
    )


def _api_key_out(k, secret: str | None = None) -> ApiKeyResponse:
    return ApiKeyResponse(
        id=k.id,
        name=k.name,
        key_prefix=k.key_prefix,
        scopes=k.scopes,
        environment=k.environment,
        rate_limit_per_minute=k.rate_limit_per_minute,
        is_active=k.is_active,
        created_at=k.created_at,
        secret=secret,
    )


def _webhook_out(h, signing_secret: str | None = None) -> WebhookResponse:
    return WebhookResponse(
        id=h.id,
        url=h.url,
        events=h.events,
        environment=getattr(h, "environment", None) or "production",
        is_active=h.is_active,
        created_at=h.created_at,
        signing_secret=signing_secret,
    )


def require_module(ctx: MerchantContext, module: str) -> None:
    try:
        _require_module(ctx, module)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=forbidden_message(module)) from exc


def _handle_permission(exc: PermissionError) -> None:
    detail = str(exc)
    if detail.startswith("merchant_forbidden:"):
        module = detail.split(":", 1)[1].split(":")[0]
        raise HTTPException(status_code=403, detail=forbidden_message(module)) from exc
    raise HTTPException(status_code=403, detail=detail) from exc


__all__ = [
    "Annotated",
    "ApiKeyCreateRequest",
    "ApiKeyResponse",
    "BillingContactRequest",
    "BillingStatementResponse",
    "BulkUploadResponse",
    "BusinessDocumentRequest",
    "Depends",
    "File",
    "HTTPException",
    "InvoiceDetailResponse",
    "InvoiceListItem",
    "MerchantApiKeyRateLimitRequest",
    "MerchantBillingHistoryItem",
    "MerchantBillingOverviewResponse",
    "MerchantBookDeliveryRequest",
    "MerchantBookingConfirmRequest",
    "MerchantBookingConfirmResponse",
    "MerchantBookingDraftResponse",
    "MerchantBookingPreviewResponse",
    "MerchantBookingTemplateCreateRequest",
    "MerchantBookingTemplateResponse",
    "MerchantBrandingRequest",
    "MerchantClaimOpenRequest",
    "MerchantConsoleRequest",
    "MerchantContactCreateRequest",
    "MerchantContactResponse",
    "MerchantContactUpdateRequest",
    "MerchantContext",
    "MerchantContractPricingResponse",
    "MerchantCreditNoteItem",
    "MerchantDashboardResponse",
    "MerchantLiveTrackingResponse",
    "MerchantMultiParcelRequest",
    "MerchantMultiParcelResponse",
    "MerchantNotificationsRequest",
    "MerchantOrder360Response",
    "MerchantOrderBulkRequest",
    "MerchantOrderFilters",
    "MerchantOrderResponse",
    "MerchantOrdersDashboardResponse",
    "MerchantPaymentItem",
    "MerchantProfileResponse",
    "MerchantProfileUpdateRequest",
    "MerchantRateCardResponse",
    "MerchantReportSaveRequest",
    "MerchantReportScheduleRequest",
    "MerchantSandboxRequest",
    "MerchantSeats",
    "MerchantStandingOrderCreateRequest",
    "MerchantStandingOrderResponse",
    "MerchantStatementDetailResponse",
    "MerchantSupportTicketRequest",
    "MerchantTaxSummaryResponse",
    "MerchantTrackingDashboardResponse",
    "MerchantTrackingEmailRequest",
    "MerchantTrackingEmailResponse",
    "MerchantTwoFactorRequest",
    "Order",
    "OrderListItem",
    "OrderListPage",
    "OrderTrackingResponse",
    "Query",
    "RecipientCreateRequest",
    "RecipientResponse",
    "RedirectResponse",
    "ReportSummaryResponse",
    "Response",
    "SavedAddressCreateRequest",
    "SavedAddressResponse",
    "Session",
    "Settings",
    "TeamInviteRequest",
    "TeamMemberResponse",
    "TeamMemberUpdateRequest",
    "TeamRoleUpdateRequest",
    "UploadFile",
    "WarehouseRequest",
    "WebhookCreateRequest",
    "WebhookResponse",
    "WebhookUpdateRequest",
    "_api_key_out",
    "_api_keys",
    "_billing",
    "_booking",
    "_booking_flow",
    "_bulk",
    "_contacts",
    "_dashboard",
    "_handle_permission",
    "_integrations",
    "_order_response",
    "_orders",
    "_privacy",
    "_profile",
    "_profile_response",
    "_reports",
    "_saved_address_out",
    "_settings",
    "_standing_orders",
    "_support",
    "_team",
    "_tracking",
    "_webhook_out",
    "get_db",
    "get_merchant_context",
    "get_merchant_seats",
    "get_settings",
    "require_module",
    "router",
]

