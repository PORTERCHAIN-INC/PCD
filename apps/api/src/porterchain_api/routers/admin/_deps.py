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


