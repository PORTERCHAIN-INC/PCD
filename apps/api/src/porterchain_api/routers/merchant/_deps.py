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


