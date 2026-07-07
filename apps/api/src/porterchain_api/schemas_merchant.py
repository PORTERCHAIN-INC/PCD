from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from porterchain_api.schemas_admin import OrderDetail360Response


class AddressInput(BaseModel):
    formatted: str
    place_id: str | None = None
    lat: float | None = None
    lng: float | None = None


class MerchantBookDeliveryRequest(BaseModel):
    pickup: AddressInput
    dropoff: AddressInput
    additional_stops: list[AddressInput] | None = None
    vehicle_class: str = "cargoVan"
    package_type: str = "looseParcel"
    weight_kg: float | None = None
    dimensions: str | None = None
    scheduled_at: datetime
    schedule_mode: str = "now"
    special_instructions: str | None = None
    internal_reference: str | None = None
    purchase_order_number: str | None = None
    cost_centre: str | None = None
    recipient_id: str | None = None
    saved_pickup_id: str | None = None
    template_id: str | None = None
    is_recurring: bool = False
    recurrence_rule: str | None = None


class MerchantBookingPreviewResponse(BaseModel):
    valid: bool
    amount_cents: int | None = None
    currency: str = "cad"
    vehicle_class: str | None = None
    vehicle_recommendation: dict[str, Any] | None = None
    contract_pricing: bool = False
    contract_id: str | None = None
    payment_terms: str | None = None
    warnings: list[str] = Field(default_factory=list)
    pricing_breakdown: dict[str, Any] | None = None
    distance_meters: int | None = None
    estimated_duration_minutes: int | None = None
    address_errors: list[dict[str, str]] = Field(default_factory=list)
    error: str | None = None
    message: str | None = None


class MerchantBookingConfirmRequest(BaseModel):
    booking: MerchantBookDeliveryRequest
    draft_id: str | None = None


class MerchantBookingConfirmResponse(BaseModel):
    order_id: str
    order_number: str
    tracking_number: str
    amount_cents: int
    preview: MerchantBookingPreviewResponse


class MerchantMultiParcelRequest(BaseModel):
    pickup: AddressInput
    parcels: list[MerchantBookDeliveryRequest]


class MerchantMultiParcelResponse(BaseModel):
    orders: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    total_amount_cents: int


class MerchantBookingDraftResponse(BaseModel):
    draft_id: str
    state: str
    current_step: str | None = None
    pickup: dict[str, Any] | None = None
    dropoff: dict[str, Any] | None = None
    vehicle_class: str | None = None
    package_type: str | None = None
    weight_kg: float | None = None
    dimensions: str | None = None
    special_instructions: str | None = None
    amount_cents: int | None = None
    pricing_breakdown: dict[str, Any] | None = None
    merchant_meta: dict[str, Any] = Field(default_factory=dict)
    expires_at: str | None = None


class MerchantBookingTemplateCreateRequest(BaseModel):
    name: str
    payload: dict[str, Any]
    is_recurring: bool = False
    recurrence_rule: str | None = None


class MerchantBookingTemplateResponse(BaseModel):
    id: str
    name: str
    payload: dict[str, Any]
    is_recurring: bool
    recurrence_rule: str | None = None
    created_at: datetime


class DashboardChartPoint(BaseModel):
    label: str
    value: int


class DashboardPerformanceCharts(BaseModel):
    daily_orders: list[DashboardChartPoint] = Field(default_factory=list)
    daily_spend_cents: list[DashboardChartPoint] = Field(default_factory=list)
    orders_by_state: list[dict[str, Any]] = Field(default_factory=list)


class DashboardDeliveryItem(BaseModel):
    order_id: str
    order_number: str
    tracking_number: str
    state: str
    amount_cents: int
    dropoff: str | None = None
    delivered_at: str


class DashboardActivityItem(BaseModel):
    id: str
    kind: str
    title: str
    detail: str | None = None
    occurred_at: str


class DashboardNotificationItem(BaseModel):
    id: str
    title: str
    body: str
    category: str
    priority: str
    deep_link: str | None = None
    is_read: bool
    created_at: str


class DashboardInvoiceLink(BaseModel):
    invoice_id: str
    invoice_number: str
    pdf_url: str | None = None
    stripe_receipt_url: str | None = None


class MerchantDashboardResponse(BaseModel):
    todays_orders: int
    awaiting_pickup: int
    in_transit: int
    delivered_today: int
    monthly_orders: int
    monthly_spend_cents: int
    outstanding_balance_cents: int
    invoices_due: int
    open_claims: int
    open_support_tickets: int
    on_time_percent: float
    delivery_success_percent: float
    payment_terms: str
    pending_dispatch: int = 0
    outstanding_invoices_cents: int = 0
    account_balance_cents: int = 0
    performance_charts: DashboardPerformanceCharts = Field(default_factory=DashboardPerformanceCharts)
    recent_deliveries: list[DashboardDeliveryItem] = Field(default_factory=list)
    recent_activity: list[DashboardActivityItem] = Field(default_factory=list)
    notifications: list[DashboardNotificationItem] = Field(default_factory=list)
    latest_invoice: DashboardInvoiceLink | None = None


class MerchantOrderResponse(BaseModel):
    order_id: str
    order_number: str
    tracking_number: str
    state: str
    amount_cents: int
    currency: str
    scheduled_at: datetime
    pickup: dict[str, Any]
    dropoff: dict[str, Any]
    internal_reference: str | None = None
    purchase_order_number: str | None = None
    fleetbase_order_id: str | None = None
    created_at: datetime


class SavedAddressResponse(BaseModel):
    id: str
    label: str
    address_type: str
    formatted: str
    is_default: bool


class RecipientResponse(BaseModel):
    id: str
    name: str
    email: str | None
    phone: str | None
    company: str | None


class BulkUploadResponse(BaseModel):
    job_id: str
    status: str
    total_rows: int
    valid_rows: int
    error_rows: int
    duplicate_rows: int
    preview: list[dict[str, Any]]
    errors: list[dict[str, Any]]


class ApiKeyCreateRequest(BaseModel):
    name: str
    scopes: list[str] = Field(default_factory=lambda: ["shipments:read", "shipments:write"])
    environment: str = "sandbox"


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    scopes: list[str]
    environment: str
    rate_limit_per_minute: int
    is_active: bool
    created_at: datetime
    secret: str | None = None


class WebhookCreateRequest(BaseModel):
    url: str
    events: list[str] = Field(default_factory=lambda: ["order.booked", "order.delivered"])


class WebhookUpdateRequest(BaseModel):
    url: str | None = None
    events: list[str] | None = None
    is_active: bool | None = None


class WebhookResponse(BaseModel):
    id: str
    url: str
    events: list[str]
    is_active: bool
    created_at: datetime | None = None
    signing_secret: str | None = None


class MerchantSandboxRequest(BaseModel):
    sandbox_mode: bool


class MerchantApiKeyRateLimitRequest(BaseModel):
    rate_limit_per_minute: int = Field(ge=10, le=600)


class MerchantConsoleRequest(BaseModel):
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)


class MerchantProfileResponse(BaseModel):
    id: str
    status: str
    company_name: str
    legal_name: str | None
    email: str
    phone: str | None
    payment_terms: str
    hst_number: str | None
    business_number: str | None
    billing_address: dict[str, Any] | None
    preferred_vehicles: list[str] | None
    delivery_zones: list[str] | None


class MerchantProfileUpdateRequest(BaseModel):
    company_name: str | None = None
    legal_name: str | None = None
    phone: str | None = None
    billing_address: dict[str, Any] | None = None
    hst_number: str | None = None
    business_number: str | None = None
    preferred_vehicles: list[str] | None = None
    delivery_zones: list[str] | None = None
    tax_exempt: bool | None = None
    tax_region: str | None = None


class InvoiceListItem(BaseModel):
    invoice_id: str
    invoice_number: str
    order_id: str
    order_number: str | None = None
    tracking_number: str | None = None
    amount_cents: int
    tax_cents: int = 0
    fees_cents: int = 0
    outstanding_cents: int = 0
    currency: str
    status: str = "sent"
    payment_terms: str = "NET_30"
    due_date: str | None = None
    created_at: datetime
    pdf_url: str | None = None
    stripe_receipt_url: str | None = None


class MerchantPaymentItem(BaseModel):
    payment_id: str
    order_id: str
    order_number: str | None = None
    tracking_number: str | None = None
    amount_cents: int
    currency: str
    status: str
    payment_method: str | None = None
    payment_reference: str | None = None
    receipt_url: str | None = None
    created_at: str | None = None


class MerchantCreditNoteItem(BaseModel):
    credit_note_id: str
    order_id: str | None = None
    order_number: str | None = None
    tracking_number: str | None = None
    amount_cents: int | None = None
    currency: str = "cad"
    reason: str | None = None
    status: str
    created_at: str | None = None


class MerchantBillingHistoryItem(BaseModel):
    kind: str
    id: str
    reference: str | None = None
    description: str
    amount_cents: int
    outstanding_cents: int | None = None
    status: str | None = None
    occurred_at: datetime | str | None = None


class MerchantTaxSummaryResponse(BaseModel):
    subtotal_cents: int
    tax_cents: int
    fees_cents: int
    total_cents: int
    invoice_count: int
    currency: str = "cad"


class MerchantContractPricingResponse(BaseModel):
    has_contract: bool
    contract_id: str | None = None
    contract_name: str | None = None
    minimum_monthly_commitment_cents: int = 0
    rules: dict[str, Any] = Field(default_factory=dict)
    pricing_config: dict[str, Any] = Field(default_factory=dict)
    effective_from: str | None = None
    effective_to: str | None = None


class BillingStatementResponse(BaseModel):
    payment_terms: str
    billing_cycle: str = "MONTHLY"
    net_terms_days: int = 30
    stripe_enabled: bool = False
    outstanding_balance_cents: int
    outstanding_invoices_cents: int = 0
    uninvoiced_orders_cents: int = 0
    credit_notes_cents: int = 0
    monthly_orders: int
    monthly_spend_cents: int
    period_start: str | None = None
    period_end: str | None = None


class MerchantBillingOverviewResponse(BillingStatementResponse):
    billing_cycles_available: list[str] = Field(default_factory=list)
    credit_limit_cents: int | None = None
    invoices_due: int = 0
    overdue_invoices: int = 0
    invoice_count: int = 0
    payment_count: int = 0
    credit_notes_count: int = 0
    tax_summary: MerchantTaxSummaryResponse
    contract_pricing: MerchantContractPricingResponse


class MerchantStatementDetailResponse(BillingStatementResponse):
    line_items: list[dict[str, Any]] = Field(default_factory=list)
    line_items_total_cents: int = 0
    monthly_orders: int
    monthly_spend_cents: int
    delivery_success_percent: float
    average_delivery_minutes: float | None
    top_routes: list[dict[str, Any]]
    invoice_summary_cents: int


class TeamMemberResponse(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool
    created_at: datetime


class TeamInviteRequest(BaseModel):
    email: str
    role: str = "merchant_ops"


class TeamRoleUpdateRequest(BaseModel):
    role: str


class MerchantContactCreateRequest(BaseModel):
    first_name: str
    last_name: str | None = None
    designation: str | None = None
    department: str | None = None
    phone: str | None = None
    mobile: str | None = None
    email: str | None = None
    linkedin: str | None = None
    roles: list[str] = Field(default_factory=list)
    is_primary: bool = False


class MerchantContactUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    designation: str | None = None
    department: str | None = None
    phone: str | None = None
    mobile: str | None = None
    email: str | None = None
    linkedin: str | None = None
    roles: list[str] | None = None
    is_primary: bool | None = None


class MerchantContactResponse(BaseModel):
    id: str
    company_id: str | None = None
    first_name: str
    last_name: str | None = None
    designation: str | None = None
    department: str | None = None
    phone: str | None = None
    mobile: str | None = None
    email: str | None = None
    linkedin: str | None = None
    birthday: str | None = None
    roles: list[str] = Field(default_factory=list)
    is_primary: bool = False
    created_at: str | None = None
    source: str = "manual"
    team_user_id: str | None = None
    team_role: str | None = None
    can_delete: bool = True


class MerchantTwoFactorRequest(BaseModel):
    enabled: bool
    method: str = "totp"


class MerchantNotificationsRequest(BaseModel):
    order_booked: bool | None = None
    order_delivered: bool | None = None
    order_failed: bool | None = None
    invoice_generated: bool | None = None
    payment_received: bool | None = None
    claim_updates: bool | None = None
    support_replies: bool | None = None
    weekly_summary: bool | None = None
    channels: dict[str, bool] | None = None


class MerchantBrandingRequest(BaseModel):
    logo_url: str | None = None
    primary_color: str | None = None
    accent_color: str | None = None
    tracking_page_message: str | None = None


class BillingContactRequest(BaseModel):
    name: str
    email: str
    phone: str | None = None
    role: str | None = None


class WarehouseRequest(BaseModel):
    name: str
    formatted: str
    lat: float | None = None
    lng: float | None = None
    is_default: bool = False


class BusinessDocumentRequest(BaseModel):
    name: str
    doc_type: str
    reference: str | None = None


class MerchantSupportTicketRequest(BaseModel):
    subject: str
    description: str | None = None
    category: str = "merchant_support"
    priority: str = "normal"
    order_id: str | None = None


class MerchantClaimOpenRequest(BaseModel):
    order_id: str
    claim_type: str
    description: str | None = None


class SavedAddressCreateRequest(BaseModel):
    label: str
    address_type: str = "pickup"
    formatted: str
    place_id: str | None = None
    lat: float | None = None
    lng: float | None = None
    is_default: bool = False


class RecipientCreateRequest(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    default_address: dict[str, Any] | None = None


class ReportSummaryResponse(BaseModel):
    monthly_orders: int
    monthly_spend_cents: int
    delivery_success_percent: float
    average_delivery_minutes: float | None
    top_routes: list[dict[str, Any]]
    invoice_summary_cents: int


class MerchantReportSaveRequest(BaseModel):
    name: str
    report_type: str
    chart_type: str = "bar"
    filters: dict[str, Any] = Field(default_factory=dict)


class MerchantReportScheduleRequest(BaseModel):
    name: str
    report_type: str
    schedule: str
    email: str


class MerchantOrderBulkRequest(BaseModel):
    order_ids: list[str]
    action: str


class MerchantOrdersDashboardResponse(BaseModel):
    orders_today: int
    orders_in_progress: int
    waiting_dispatch: int
    assigned: int
    picked_up: int
    delivered: int
    failed: int
    returned: int
    claims: int
    open_support_tickets: int
    revenue_today_cents: int
    avg_delivery_hours: float
    avg_pickup_hours: float
    avg_sla_percent: float


class MerchantOrder360Response(OrderDetail360Response):
    merchant_activity: list[dict[str, Any]] = Field(default_factory=list)


class OrderTrackingResponse(BaseModel):
    order: MerchantOrderResponse
    timeline: list[dict[str, Any]]
    live_tracking: dict[str, Any] | None = None


class MerchantTrackingDashboardResponse(BaseModel):
    active_count: int
    orders: list[dict[str, Any]]
    geofences: list[dict[str, Any]] = Field(default_factory=list)
    updated_at: str


class MerchantLiveTrackingResponse(BaseModel):
    order_id: str
    tracking_number: str
    order_number: str | None = None
    state: str
    scheduled_at: str | None = None
    pickup: dict[str, Any] | None = None
    dropoff: dict[str, Any] | None = None
    fleetbase_order_id: str | None = None
    driver: dict[str, Any] | None = None
    vehicle: dict[str, Any] | None = None
    driver_location: dict[str, Any] | None = None
    live: dict[str, Any] | None = None
    eta: dict[str, Any] | None = None
    optimized_route: dict[str, Any] | None = None
    delivery_status: dict[str, Any] | None = None
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    tracking_history: list[dict[str, Any]] = Field(default_factory=list)
    replay: list[dict[str, Any]] = Field(default_factory=list)
    proof_of_delivery: dict[str, Any] = Field(default_factory=dict)
    geofences: list[dict[str, Any]] = Field(default_factory=list)
    notifications: list[dict[str, Any]] = Field(default_factory=list)
    last_updated: str | None = None
