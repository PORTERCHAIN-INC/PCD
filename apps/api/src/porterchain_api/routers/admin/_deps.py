"""Admin operations API — /v1/admin/*"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import commit_admin_audit, commit_admin_write, log_admin_audit
from porterchain_api.admin_engine.claims_service import AdminClaimsService, ClaimFilters
from porterchain_api.admin_engine.dashboard_service import AdminDashboardService
from porterchain_api.admin_engine.finance_service import AdminFinanceService, FinanceFilters
from porterchain_api.admin_engine.operations_service import AdminOperationsService
from porterchain_api.admin_engine.orders_service import AdminOrderFilters, AdminOrdersService
from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.admin_engine.clerk_directory_service import ClerkDirectoryService
from porterchain_api.admin_engine.settings_service import AdminSettingsService
from porterchain_api.admin_engine.support_service import AdminSupportService, SupportFilters
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.merchant_models import Merchant
from porterchain_api.booking_models import Order
from porterchain_api.schemas_admin import (
    AdminDashboardResponse,
    AssignDriverRequest,
    ClaimCreateRequest,
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
    OrderListPage,
    OrderDashboardResponse,
    OrderDetailResponse,
    OrderDetail360Response,
    OrderBulkRequest,
    OrderTemperatureRequest,
    AdminCreateOrderRequest,
    AdminCreateOrderResponse,
    PaymentAdminItem,
    StaffItem,
    StaffInviteRequest,
    StaffEnrollResponse,
    StaffRoleUpdateRequest,
    PlatformUserItem,
    PlatformUsersResponse,
    PlatformUserCreateRequest,
    PlatformUserUpdateRequest,
    PlatformUserDeleteRequest,
    PlatformUserInviteRequest,
    PlatformUserAuthorizeRequest,
    PlatformUserAuthorizeResponse,
    ImpersonationStartRequest,
    ImpersonationStopRequest,
    ImpersonationSessionResponse,
    SettingsConfigUpdateRequest,
    SettingsImportRequest,
    TicketCreateRequest,
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
    FinanceDashboardResponse,
    FinanceCollectionItem,
    FinanceInvoiceItem,
    FinanceInvoicePage,
    FinanceInvoiceDetailResponse,
    FinancePaymentItem,
    FinancePaymentPage,
    FinancePayoutItem,
    FinanceLedgerItem,
    FinanceCreditNoteRequest,
    MerchantArGenerateRequest,
    MerchantArRecordPaymentRequest,
    BookingDraftAdminItem,
    BookingDraftAdminDetailResponse,
    BookingDraftAnalyticsResponse,
    BookingDraftAbandonedItem,
    BookingDraftExtendRequest,
    BookingDraftCancelRequest,
    BookingDraftBulkRequest,
    BookingDraftPaymentLinkResponse,
    BlogAuthorCreateRequest,
    BlogAuthorItem,
    BlogAuthorUpdateRequest,
    BlogPostCreateRequest,
    BlogPostItem,
    BlogPostUpdateRequest,
    RouteTemplateCreateRequest,
    RouteTemplateItem,
    RouteTemplateUpdateRequest,
)
from porterchain_api.admin_engine.booking_draft_admin_service import (
    AdminBookingDraftService,
    AdminDraftFilters,
)
from porterchain_api.admin_engine.audit_export_service import AdminAuditExportService
from porterchain_api.admin_engine.data_moat_service import AdminDataMoatService
from porterchain_api.admin_engine.investor_metrics_service import InvestorMetricsService
from porterchain_api.admin_engine.monopoly_metrics_service import MonopolyMetricsService
from porterchain_api.admin_engine.platform_metrics_service import PlatformMetricsService
from porterchain_api.content_engine.blog_service import BlogService
from porterchain_api.admin_engine.route_template_service import AdminRouteTemplateService
router = APIRouter(prefix="/v1/admin", tags=["admin"])

_dashboard = AdminDashboardService()
_ops = AdminOperationsService()
_orders = AdminOrdersService()
_claims = AdminClaimsService()
_finance = AdminFinanceService()
_merchant_ar = __import__(
    "porterchain_api.admin_engine.merchant_ar_service", fromlist=["MerchantArService"]
).MerchantArService()
_support = AdminSupportService()
_settings = AdminSettingsService()
_clerk_directory = ClerkDirectoryService()
_draft_admin = AdminBookingDraftService()
_blog = BlogService()
_data_moat = AdminDataMoatService()
_platform_metrics = PlatformMetricsService()
_investor_metrics = InvestorMetricsService()
_monopoly_metrics = MonopolyMetricsService()
_audit_export = AdminAuditExportService()
_route_templates = AdminRouteTemplateService()


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


__all__ = [
    "AdminContext",
    "AdminDashboardResponse",
    "AdminDraftFilters",
    "AdminOrderFilters",
    "Annotated",
    "AssignDriverRequest",
    "BookingDraftAbandonedItem",
    "BookingDraftAdminDetailResponse",
    "BookingDraftAdminItem",
    "BookingDraftAnalyticsResponse",
    "BookingDraftBulkRequest",
    "BookingDraftCancelRequest",
    "BookingDraftExtendRequest",
    "BookingDraftPaymentLinkResponse",
    "BlogAuthorCreateRequest",
    "BlogAuthorItem",
    "BlogAuthorUpdateRequest",
    "BlogPostCreateRequest",
    "BlogPostItem",
    "BlogPostUpdateRequest",
    "RouteTemplateCreateRequest",
    "RouteTemplateItem",
    "RouteTemplateUpdateRequest",
    "ClaimAssignRequest",
    "ClaimBulkRequest",
    "ClaimCompensationRequest",
    "ClaimCreateRequest",
    "ClaimDashboardResponse",
    "ClaimDetailResponse",
    "ClaimEvidenceRequest",
    "ClaimFilters",
    "ClaimInsuranceRequest",
    "ClaimInvestigationRequest",
    "ClaimListItem",
    "ClaimNoteRequest",
    "ClaimStatusUpdateRequest",
    "Depends",
    "FinanceCreditNoteRequest",
    "MerchantArGenerateRequest",
    "MerchantArRecordPaymentRequest",
    "FinanceDashboardResponse",
    "FinanceFilters",
    "FinanceInvoiceDetailResponse",
    "FinanceCollectionItem",
    "FinanceInvoiceItem",
    "FinanceInvoicePage",
    "FinanceLedgerItem",
    "FinancePaymentItem",
    "FinancePaymentPage",
    "FinancePayoutItem",
            "HTTPException",
    "Merchant",
            "OrderAdminItem",
    "OrderBulkRequest",
    "OrderTemperatureRequest",
    "AdminCreateOrderRequest",
    "AdminCreateOrderResponse",
    "OrderDashboardResponse",
    "OrderDetail360Response",
    "OrderListItem",
    "OrderListPage",
    "PlatformUserCreateRequest",
    "PlatformUserDeleteRequest",
    "PlatformUserInviteRequest",
    "PlatformUserAuthorizeRequest",
    "PlatformUserAuthorizeResponse",
    "ImpersonationStartRequest",
    "ImpersonationStopRequest",
    "ImpersonationSessionResponse",
    "PlatformUserUpdateRequest",
    "PlatformUsersResponse",
    "Query",
    "Session",
    "Settings",
    "SettingsConfigUpdateRequest",
    "SettingsImportRequest",
    "StaffInviteRequest",
    "StaffEnrollResponse",
    "StaffItem",
    "StaffRoleUpdateRequest",
    "SupportAutomationRequest",
    "SupportFilters",
    "SupportKbArticleRequest",
    "SupportMacroRequest",
    "SupportSlaConfigRequest",
                    "TicketAssignRequest",
    "TicketBulkRequest",
    "TicketCreateRequest",
    "TicketDashboardResponse",
    "TicketDetailResponse",
    "TicketListItem",
    "TicketNoteRequest",
    "TicketStatusRequest",
    "_audit_export",
    "_claims",
    "_data_moat",
    "_clerk_directory",
    "_dashboard",
    "_draft_admin",
    "_finance",
    "_investor_metrics",
    "_monopoly_metrics",
    "_ops",
    "_order_detail",
    "_order_item",
    "_orders",
    "_perm",
    "_platform_metrics",
    "_blog",
    "_route_templates",
    "_settings",
    "_support",
    "get_admin_context",
    "get_db",
    "get_settings",
    "commit_admin_audit",
    "commit_admin_write",
    "log_admin_audit",
    "require_module",
    "router",
]

# Re-exports kept for existing importers (integration).
from porterchain_api.schemas_admin import PlatformUserItem  # noqa: E402, F401
