from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AdminDashboardResponse(BaseModel):
    todays_revenue_cents: int
    todays_bookings: int
    pending_quotes: int
    pending_merchant_approvals: int
    drivers_online: int
    drivers_offline: int
    orders_waiting_dispatch: int
    orders_in_transit: int
    completed_today: int
    failed_deliveries: int
    open_claims: int
    outstanding_invoices_cents: int
    open_support_tickets: int
    fleet_health_percent: float


class CrmSummaryResponse(BaseModel):
    visitor_leads: int
    quote_requests: int
    abandoned_checkouts: int
    business_inquiries: int
    open_tasks: int


class LeadItem(BaseModel):
    id: str
    source: str
    email: str
    phone: str | None
    stage: str
    quote_id: str | None
    created_at: datetime


class MerchantAdminItem(BaseModel):
    id: str
    status: str
    company_name: str
    email: str
    payment_terms: str
    created_at: datetime


class MerchantUpdateRequest(BaseModel):
    payment_terms: str | None = None
    pricing_config: dict[str, Any] | None = None
    credit_limit_cents: int | None = None
    parent_merchant_id: str | None = None
    support_tier: str | None = Field(default=None, pattern="^(standard|priority|enterprise)$")


class MerchantInviteRequest(BaseModel):
    email: str
    role: str | None = None


class MerchantInviteResponse(BaseModel):
    merchant_user_id: str
    email: str
    role: str
    invitation_status: str
    clerk_user_id: str | None = None


class MerchantCreateRequest(BaseModel):
    email: str
    company_name: str
    auto_activate: bool = True
    send_invite: bool = True


class MerchantActivateUsersRequest(BaseModel):
    email: str | None = None


class MerchantCompleteOnboardingRequest(BaseModel):
    email: str | None = None


class DriverItem(BaseModel):
    id: str
    status: str
    full_name: str
    email: str
    phone: str | None
    license_verified: bool
    insurance_verified: bool
    vehicle_verified: bool
    background_check_status: str
    rating: float | None
    is_online: bool
    wallet_balance_cents: int
    created_at: datetime


class DriverVerifyRequest(BaseModel):
    license_verified: bool | None = None
    medical_transport_certified: bool | None = None
    insurance_verified: bool | None = None
    vehicle_verified: bool | None = None
    background_check_status: str | None = None


class DriverAddressInput(BaseModel):
    street: str | None = None
    city: str | None = None
    province: str | None = None
    postal_code: str | None = None


class DriverEmergencyContactInput(BaseModel):
    name: str | None = None
    phone: str | None = None
    relationship: str | None = None


class DriverVehicleCreateInput(BaseModel):
    vehicle_class: str
    plate_number: str
    make_model: str | None = None
    capacity_kg: float | None = None
    compliance_expires_at: datetime | None = None


class DriverDocumentInput(BaseModel):
    doc_type: str = Field(min_length=1, max_length=64)
    label: str | None = Field(default=None, max_length=255)
    file_url: str | None = Field(default=None, max_length=2048)
    reference_number: str | None = Field(default=None, max_length=128)
    expires_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)


class DriverCreateRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=320)
    phone: str | None = Field(default=None, max_length=32)
    license_class: str | None = Field(default=None, max_length=32)
    license_number: str | None = Field(default=None, max_length=64)
    service_area: str | None = Field(default=None, max_length=128)
    employment_type: str | None = Field(default=None, max_length=64)
    address: DriverAddressInput | None = None
    emergency_contact: DriverEmergencyContactInput | None = None
    vehicle: DriverVehicleCreateInput | None = None
    documents: list[DriverDocumentInput] = Field(default_factory=list)
    auto_approve: bool = False


class OrderAdminItem(BaseModel):
    order_id: str
    order_number: str
    tracking_number: str
    state: str
    amount_cents: int
    currency: str
    merchant_id: str | None
    customer_id: str | None
    scheduled_at: datetime
    pickup: dict[str, Any]
    dropoff: dict[str, Any]
    created_at: datetime


class OrderListItem(BaseModel):
    order_id: str
    order_number: str
    tracking_number: str
    booking_number: str | None = None
    merchant_id: str | None = None
    merchant_name: str | None = None
    customer_id: str | None = None
    customer_email: str | None = None
    driver_id: str | None = None
    driver_name: str | None = None
    vehicle_label: str | None = None
    pickup: str
    destination: str
    service_type: str | None = None
    priority: str = "normal"
    state: str
    display_state: str
    payment_status: str | None = None
    invoice_status: str = "none"
    amount_cents: int
    currency: str = "cad"
    eta: datetime | None = None
    sla_status: str = "ok"
    fraud_risk_score: int = 0
    delay_risk_score: int = 0
    scheduled_at: datetime
    created_at: datetime
    updated_at: datetime


class OrderDashboardResponse(BaseModel):
    orders_today: int
    orders_in_progress: int
    waiting_dispatch: int
    assigned: int
    picked_up: int
    delivered: int
    failed: int
    returned: int
    claims: int
    revenue_today_cents: int
    avg_delivery_hours: float
    avg_pickup_hours: float
    avg_sla_percent: float


class OrderBulkRequest(BaseModel):
    order_ids: list[str]
    action: str
    driver_id: str | None = None


class OrderTemperatureRequest(BaseModel):
    celsius: float = Field(..., description="Recorded cargo temperature in °C")


class PaymentAdminItem(BaseModel):
    payment_id: str
    status: str
    amount_cents: int
    currency: str
    stripe_payment_intent_id: str | None = None
    stripe_checkout_session_id: str | None = None
    receipt_url: str | None = None
    failure_reason: str | None = None
    retry_count: int = 0
    created_at: datetime


class OrderDetailResponse(BaseModel):
    # Order
    order_id: str
    order_number: str
    tracking_number: str
    state: str
    amount_cents: int
    currency: str
    scheduled_at: datetime
    created_at: datetime
    pickup: dict[str, Any]
    dropoff: dict[str, Any]
    special_instructions: str | None = None
    fleetbase_order_id: str | None = None
    assigned_driver_id: str | None = None
    # Customer
    customer_id: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None
    # Booking
    booking_number: str | None = None
    # Quote / pricing snapshot captured at booking time
    quote_id: str | None = None
    vehicle_class: str | None = None
    package_type: str | None = None
    weight_kg: float | None = None
    dimensions: str | None = None
    declared_value_cents: int | None = None
    distance_meters: int | None = None
    quote_amount_cents: int | None = None
    pricing_breakdown: dict[str, Any] | None = None
    # Payments + invoice
    payments: list[PaymentAdminItem] = Field(default_factory=list)
    invoice_number: str | None = None
    invoice_amount_cents: int | None = None
    invoice_receipt_url: str | None = None
    invoice_pdf_url: str | None = None


class OrderDetail360Response(OrderListItem):
    special_instructions: str | None = None
    fleetbase_order_id: str | None = None
    customer_phone: str | None = None
    booking_id: str | None = None
    booking_draft_id: str | None = None
    booking_draft_number: str | None = None
    quote_id: str | None = None
    vehicle_class: str | None = None
    package_type: str | None = None
    weight_kg: float | None = None
    dimensions: str | None = None
    declared_value_cents: int | None = None
    distance_meters: int | None = None
    quote_amount_cents: int | None = None
    pricing_breakdown: dict[str, Any] | None = None
    pickup_detail: dict[str, Any] = Field(default_factory=dict)
    dropoff_detail: dict[str, Any] = Field(default_factory=dict)
    additional_stops: list[Any] = Field(default_factory=list)
    payments: list[PaymentAdminItem] = Field(default_factory=list)
    invoice_number: str | None = None
    invoice_amount_cents: int | None = None
    invoice_receipt_url: str | None = None
    invoice_pdf_url: str | None = None
    merchant: dict[str, Any] | None = None
    customer_360: dict[str, Any] | None = None
    driver: dict[str, Any] | None = None
    vehicle: dict[str, Any] | None = None
    driver_status: str | None = None
    vehicle_status: str | None = None
    parcel_count: int = 1
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    tracking: dict[str, Any] | None = None
    packages: list[dict[str, Any]] = Field(default_factory=list)
    incidents: list[dict[str, Any]] = Field(default_factory=list)
    claims: list[dict[str, Any]] = Field(default_factory=list)
    support_tickets: list[dict[str, Any]] = Field(default_factory=list)
    documents: list[dict[str, Any]] = Field(default_factory=list)
    proof_of_delivery: dict[str, Any] = Field(default_factory=dict)
    domain_events: list[dict[str, Any]] = Field(default_factory=list)
    audit_log: list[dict[str, Any]] = Field(default_factory=list)
    internal_notes: list[dict[str, Any]] = Field(default_factory=list)
    automation: list[dict[str, Any]] = Field(default_factory=list)
    communications: list[dict[str, Any]] = Field(default_factory=list)
    api_activity: list[dict[str, Any]] = Field(default_factory=list)
    duplicates: list[dict[str, Any]] = Field(default_factory=list)
    smart: dict[str, Any] = Field(default_factory=dict)


class AssignDriverRequest(BaseModel):
    driver_id: str


class ClaimItem(BaseModel):
    id: str
    order_id: str
    claim_type: str
    status: str
    description: str | None
    created_at: datetime


class ClaimListItem(BaseModel):
    id: str
    claim_number: str
    claim_type: str
    priority: str = "normal"
    status: str
    display_status: str
    merchant_id: str | None = None
    merchant_name: str | None = None
    customer_id: str | None = None
    customer_email: str | None = None
    driver_id: str | None = None
    driver_name: str | None = None
    order_id: str
    tracking_number: str | None = None
    order_number: str | None = None
    amount_cents: int = 0
    has_insurance: bool = False
    assigned_investigator_id: str | None = None
    assigned_investigator: str | None = None
    risk_score: int = 0
    description: str | None = None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None


class ClaimDetailResponse(ClaimListItem):
    evidence_files: list[dict[str, Any]] = Field(default_factory=list)
    communications: list[dict[str, Any]] = Field(default_factory=list)
    investigation: dict[str, Any] = Field(default_factory=dict)
    internal_notes: list[dict[str, Any]] = Field(default_factory=list)
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    compensation: dict[str, Any] = Field(default_factory=dict)
    insurance: dict[str, Any] = Field(default_factory=dict)
    order: dict[str, Any] = Field(default_factory=dict)
    domain_events: list[dict[str, Any]] = Field(default_factory=list)
    duplicates: list[dict[str, Any]] = Field(default_factory=list)
    smart: dict[str, Any] = Field(default_factory=dict)


class ClaimDashboardResponse(BaseModel):
    open_claims: int
    under_investigation: int
    waiting_merchant: int
    waiting_customer: int
    waiting_driver: int
    insurance_claims: int
    chargebacks: int
    resolved_claims: int
    rejected_claims: int
    avg_resolution_hours: float
    total_compensation_cents: int
    monthly_claims: int
    avg_risk_score: float


class ClaimCreateRequest(BaseModel):
    order_id: str
    claim_type: str
    description: str | None = None
    priority: str = "normal"


class ClaimStatusUpdateRequest(BaseModel):
    status: str


class ClaimAssignRequest(BaseModel):
    investigator_id: str


class ClaimEvidenceRequest(BaseModel):
    file_type: str
    name: str
    url: str | None = None
    meta: dict[str, Any] | None = None


class ClaimNoteRequest(BaseModel):
    body: str
    internal: bool = True
    channel: str = "internal"


class ClaimInvestigationRequest(BaseModel):
    root_cause: str | None = None
    driver_review: str | None = None
    merchant_review: str | None = None
    customer_review: str | None = None
    vehicle_review: str | None = None
    gps_review: str | None = None
    timeline_review: str | None = None
    evidence_review: str | None = None
    internal_notes: str | None = None


class ClaimCompensationRequest(BaseModel):
    claim_amount_cents: int | None = None
    approved_amount_cents: int | None = None
    currency: str = "cad"
    refund_cents: int | None = None
    credit_note_cents: int | None = None
    wallet_credit_cents: int | None = None
    insurance_payout_cents: int | None = None
    driver_liability_cents: int | None = None
    merchant_liability_cents: int | None = None
    customer_compensation_cents: int | None = None


class ClaimInsuranceRequest(BaseModel):
    provider: str | None = None
    policy_number: str | None = None
    claim_reference: str | None = None
    adjuster: str | None = None
    status: str | None = None
    settlement_cents: int | None = None
    documents: list[dict[str, Any]] | None = None


class ClaimBulkRequest(BaseModel):
    claim_ids: list[str]
    action: str
    investigator_id: str | None = None
    status: str | None = None


class TicketItem(BaseModel):
    id: str
    status: str
    priority: str
    subject: str
    order_id: str | None
    created_at: datetime


class TicketListItem(BaseModel):
    id: str
    ticket_number: str
    subject: str
    category: str
    priority: str
    status: str
    display_status: str
    customer_id: str | None = None
    customer_email: str | None = None
    merchant_id: str | None = None
    merchant_name: str | None = None
    driver_id: str | None = None
    driver_name: str | None = None
    order_id: str | None = None
    order_number: str | None = None
    tracking_number: str | None = None
    booking_id: str | None = None
    booking_number: str | None = None
    assigned_agent_id: str | None = None
    assigned_agent: str | None = None
    sla_status: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class TicketDetailResponse(TicketListItem):
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    communications: list[dict[str, Any]] = Field(default_factory=list)
    internal_notes: list[dict[str, Any]] = Field(default_factory=list)
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    customer: dict[str, Any] | None = None
    merchant: dict[str, Any] | None = None
    driver: dict[str, Any] | None = None
    order: dict[str, Any] | None = None
    booking: dict[str, Any] | None = None
    tracking: dict[str, Any] | None = None
    invoice: dict[str, Any] | None = None
    payment: dict[str, Any] | None = None
    claims: list[dict[str, Any]] = Field(default_factory=list)
    documents: list[dict[str, Any]] = Field(default_factory=list)
    domain_events: list[dict[str, Any]] = Field(default_factory=list)
    audit_log: list[dict[str, Any]] = Field(default_factory=list)
    sla: dict[str, Any] = Field(default_factory=dict)
    duplicates: list[dict[str, Any]] = Field(default_factory=list)
    smart: dict[str, Any] = Field(default_factory=dict)


class TicketDashboardResponse(BaseModel):
    open_tickets: int
    urgent_tickets: int
    sla_breaches: int
    pending_customer: int
    pending_merchant: int
    pending_driver: int
    pending_internal: int
    claims_linked: int
    orders_impacted: int
    avg_first_response_hours: float
    avg_resolution_hours: float
    customer_satisfaction: float
    recent_activity: list[dict[str, Any]] = Field(default_factory=list)
    team_workload: list[dict[str, Any]] = Field(default_factory=list)


class TicketCreateRequest(BaseModel):
    subject: str
    description: str | None = None
    priority: str = "normal"
    category: str = "general_inquiry"
    order_id: str | None = None
    customer_id: str | None = None
    merchant_id: str | None = None
    driver_id: str | None = None


class TicketStatusRequest(BaseModel):
    status: str


class TicketAssignRequest(BaseModel):
    agent_id: str


class TicketNoteRequest(BaseModel):
    body: str
    internal: bool = True
    channel: str = "note"


class TicketBulkRequest(BaseModel):
    ticket_ids: list[str]
    action: str
    agent_id: str | None = None
    status: str | None = None


class SupportKbArticleRequest(BaseModel):
    id: str | None = None
    category_id: str
    title: str
    body: str
    published: bool = True


class SupportMacroRequest(BaseModel):
    id: str | None = None
    title: str
    body: str
    channel: str = "email"


class SupportAutomationRequest(BaseModel):
    auto_assign: bool | None = None
    auto_escalate_breached_sla: bool | None = None
    auto_close_resolved_days: int | None = None
    auto_reminder_hours: int | None = None
    auto_tagging: bool | None = None
    auto_categorization: bool | None = None
    auto_merge_duplicates: bool | None = None


class SupportSlaConfigRequest(BaseModel):
    first_response_hours: int | None = None
    resolution_hours: int | None = None
    escalation_hours: int | None = None
    business_hours_only: bool | None = None


class TariffItem(BaseModel):
    id: str
    name: str
    tariff_type: str
    vehicle_class: str | None
    zone: str | None
    merchant_id: str | None = None
    merchant_name: str | None = None
    base_cents: int
    per_km_cents: int
    fuel_surcharge_percent: float
    is_active: bool
    status: str = "published"
    version: int = 1
    priority: int = 100
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    created_at: datetime | None = None


class TariffUpdateRequest(BaseModel):
    name: str | None = None
    base_cents: int | None = None
    per_km_cents: int | None = None
    fuel_surcharge_percent: float | None = None
    is_active: bool | None = None
    config: dict[str, Any] | None = None


class PricingDashboardResponse(BaseModel):
    active_pricing_rules: int
    merchant_contracts: int
    vehicle_pricing_rules: int
    zone_pricing_rules: int
    distance_pricing_rules: int
    weight_pricing_rules: int
    fuel_surcharge_percent: float
    tax_hst_percent: float
    active_coupons: int
    active_promotions: int
    revenue_forecast_cents: int
    monthly_quotes: int
    recent_changes: list[dict[str, Any]] = Field(default_factory=list)
    upcoming_scheduled: list[dict[str, Any]] = Field(default_factory=list)
    conflict_count: int = 0


class TariffCreateRequest(BaseModel):
    name: str
    tariff_type: str
    vehicle_class: str | None = None
    zone: str | None = None
    merchant_id: str | None = None
    base_cents: int = 0
    per_km_cents: int = 0
    fuel_surcharge_percent: float = 0.0
    config: dict[str, Any] = Field(default_factory=dict)


class ReportsSummaryResponse(BaseModel):
    monthly_orders: int
    monthly_revenue_cents: int
    active_merchants: int
    active_drivers: int
    delivery_sla_percent: float
    cancellation_rate_percent: float
    claim_rate_percent: float


class ReportSaveRequest(BaseModel):
    name: str
    category_id: str
    chart_type: str = "bar"
    filters: dict[str, Any] = Field(default_factory=dict)
    pinned: bool = False


class ReportScheduleRequest(BaseModel):
    name: str
    category_id: str
    schedule: str
    email: str


class ReportBuilderPreviewRequest(BaseModel):
    dataset: str
    group_by: str
    metric: str = "count"


class ReportExportAuditRequest(BaseModel):
    report_id: str
    format: str


class StaffItem(BaseModel):
    id: str
    email: str
    name: str | None
    role: str
    created_at: datetime


class PlatformUserItem(BaseModel):
    """Unified directory row for Settings → Users tabs."""

    id: str
    user_type: str  # staff | driver | customer | merchant
    email: str
    name: str | None = None
    role: str | None = None
    status: str | None = None  # domain / account status (APPROVED, active, …)
    organization: str | None = None
    access_status: str  # authorized | pending_review | suspended | inactive | not_authorized | merchant_inactive
    invite_status: str  # not_invited | invite_pending | accepted | revoked | invite_failed
    identity_status: str  # registered | invite_pending | not_registered
    status_label: str
    clerk_linked: bool = False
    clerk_user_id: str | None = None
    provisioned: bool = True
    clerk_status: str | None = None  # active | banned | locked | never_signed_in
    clerk_email_verified: bool = False
    clerk_password_set: bool = False
    clerk_last_sign_in_at: datetime | None = None
    detail_href: str | None = None
    created_at: datetime


class PlatformUsersFacets(BaseModel):
    access_status: dict[str, int] = Field(default_factory=dict)
    invite_status: dict[str, int] = Field(default_factory=dict)
    identity_status: dict[str, int] = Field(default_factory=dict)
    account_status: dict[str, int] = Field(default_factory=dict)
    clerk_status: dict[str, int] = Field(default_factory=dict)


class PlatformUsersResponse(BaseModel):
    items: list[PlatformUserItem]
    total: int
    facets: PlatformUsersFacets
    clerk_synced: bool = False
    clerk_total: int | None = None


class PlatformUserCreateRequest(BaseModel):
    email: str
    name: str | None = None
    role: str | None = None
    password: str | None = None
    send_invite: bool = True
    merchant_id: str | None = None


class PlatformUserUpdateRequest(BaseModel):
    clerk_user_id: str
    name: str | None = None
    password: str | None = None
    banned: bool | None = None


class PlatformUserDeleteRequest(BaseModel):
    clerk_user_id: str | None = None
    platform_user_id: str | None = None


class StaffRoleUpdateRequest(BaseModel):
    role: str
    reason: str | None = None


class StaffInviteRequest(BaseModel):
    email: str
    role: str
    name: str | None = None


class StaffInviteResponse(BaseModel):
    id: str
    email: str
    name: str | None
    role: str
    clerk_action: str
    invitation_status: str
    created_at: datetime


class SettingsConfigUpdateRequest(BaseModel):
    value: Any
    reason: str | None = None


class SettingsImportRequest(BaseModel):
    config: dict[str, Any]
    reason: str | None = None


class CrmTaskCreateRequest(BaseModel):
    title: str
    lead_id: str | None = None
    merchant_id: str | None = None


class CrmNoteCreateRequest(BaseModel):
    entity_type: str
    entity_id: str
    body: str


class PromotionItem(BaseModel):
    id: str
    code: str
    promotion_type: str
    merchant_id: str | None
    merchant_name: str | None = None
    discount_percent: float | None
    discount_cents: int | None
    is_active: bool
    expires_at: datetime | None = None
    status: str = "published"
    created_at: datetime | None = None


class PromotionCreateRequest(BaseModel):
    code: str
    promotion_type: str = "coupon"
    merchant_id: str | None = None
    discount_percent: float | None = None
    discount_cents: int | None = None
    is_active: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class PricingZoneItem(BaseModel):
    id: str
    code: str
    name: str
    multiplier: float
    is_active: bool
    bounds: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class PricingZoneCreateRequest(BaseModel):
    code: str
    name: str
    bounds: dict[str, float]
    multiplier: float = 1.0


class MerchantContractItem(BaseModel):
    id: str
    merchant_id: str
    merchant_name: str | None = None
    name: str
    minimum_monthly_commitment_cents: int
    is_active: bool
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    created_at: datetime | None = None


class MerchantContractCreateRequest(BaseModel):
    merchant_id: str
    name: str
    rules: dict[str, Any] = Field(default_factory=dict)
    minimum_monthly_commitment_cents: int = 0


class PricingSimulatorRequest(BaseModel):
    pickup: dict[str, Any]
    dropoff: dict[str, Any]
    vehicle_class: str
    package_type: str = "looseParcel"
    service_type: str = "same_day"
    weight_kg: float | None = None
    dimensions: str | dict[str, float] | None = None
    declared_value_cents: int | None = None
    schedule_mode: str = "now"
    channel: str = "retail"
    merchant_id: str | None = None
    promo_code: str | None = None
    distance_meters: int | None = None
    overrides: dict[str, Any] | None = None


class PricingBreakdownResponse(BaseModel):
    base_cents: int
    distance_cents: int
    vehicle_cents: int
    weight_cents: int
    fuel_cents: int
    tax_cents: int
    discount_cents: int
    subtotal_cents: int
    final_cents: int
    currency: str = "cad"
    zone_code: str | None = None
    contract_id: str | None = None
    promo_code: str | None = None
    items: list[dict[str, Any]]
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaxConfigRequest(BaseModel):
    hst_percent: float = 13.0
    tax_included: bool = False
    exempt_merchant_ids: list[str] = Field(default_factory=list)


class FuelConfigRequest(BaseModel):
    surcharge_percent: float = 8.5
    base_fuel_price_cents: int = 145
    current_fuel_price_cents: int = 158


class FinanceDashboardResponse(BaseModel):
    today_revenue_cents: int
    month_revenue_cents: int
    outstanding_invoices_cents: int
    paid_invoices_cents: int
    outstanding_invoice_count: int
    paid_invoice_count: int
    pending_payments: int
    paid_payments_count: int
    refunds_count: int
    credit_notes_count: int
    merchant_balances_cents: int
    driver_payouts_pending_cents: int
    driver_payouts_paid_cents: int
    driver_wallets_cents: int
    taxes_collected_cents: int
    profit_estimate_cents: int
    payment_success_rate: float
    overdue_invoices_count: int
    revenue_trend: list[dict[str, Any]] = Field(default_factory=list)
    cash_flow_cents: int
    top_merchants: list[dict[str, Any]] = Field(default_factory=list)
    revenue_forecast_cents: int


class FinanceInvoiceItem(BaseModel):
    invoice_id: str
    invoice_number: str
    receipt_number: str | None = None
    status: str
    merchant_id: str | None = None
    merchant_name: str | None = None
    customer_id: str
    customer_email: str | None = None
    order_id: str
    order_number: str | None = None
    tracking_number: str | None = None
    booking_number: str | None = None
    amount_cents: int
    tax_cents: int
    fees_cents: int
    outstanding_cents: int
    currency: str
    payment_terms: str = "IMMEDIATE"
    due_date: datetime | None = None
    pdf_url: str | None = None
    receipt_url: str | None = None
    created_at: datetime


class FinanceInvoiceDetailResponse(FinanceInvoiceItem):
    payment: dict[str, Any] | None = None
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    audit_log: list[dict[str, Any]] = Field(default_factory=list)
    duplicates: list[dict[str, Any]] = Field(default_factory=list)


class FinancePaymentItem(BaseModel):
    payment_id: str
    status: str
    amount_cents: int
    currency: str
    payment_method: str
    stripe_payment_intent_id: str | None = None
    payment_reference: str | None = None
    transaction_id: str | None = None
    order_id: str | None = None
    order_number: str | None = None
    tracking_number: str | None = None
    customer_email: str | None = None
    receipt_url: str | None = None
    failure_reason: str | None = None
    created_at: datetime


class FinancePayoutItem(BaseModel):
    payout_id: str
    driver_id: str
    driver_name: str | None = None
    amount_cents: int
    currency: str
    status: str
    reference: str | None = None
    created_at: datetime


class FinanceLedgerItem(BaseModel):
    id: str
    kind: str
    payment_id: str | None = None
    order_id: str | None = None
    merchant_id: str | None = None
    amount_cents: int | None = None
    currency: str
    status: str
    created_at: datetime


class FinanceCreditNoteRequest(BaseModel):
    order_id: str
    amount_cents: int
    reason: str


class BookingDraftAdminItem(BaseModel):
    draft_id: str
    draft_number: str
    session_id: str
    visitor_id: str | None = None
    customer_id: str | None
    customer_email: str | None
    merchant_id: str | None = None
    merchant_name: str | None = None
    quote_id: str | None
    booking_type: str = "individual"
    state: str
    display_state: str
    current_step: str
    payment_status: str | None
    vehicle_class: str | None = None
    amount_cents: int | None
    currency: str = "cad"
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    is_expired: bool = False
    is_abandoned: bool = False
    booking_id: str | None = None
    order_id: str | None = None


class BookingDraftAdminDetailResponse(BookingDraftAdminItem):
    pickup: dict[str, Any] | None = None
    dropoff: dict[str, Any] | None = None
    additional_stops: list | None = None
    package_type: str | None = None
    weight_kg: float | None = None
    dimensions: str | None = None
    declared_value_cents: int | None = None
    special_instructions: str | None = None
    pricing_breakdown: dict[str, Any] | None = None
    taxes_cents: int = 0
    discounts_cents: int = 0
    promo_code: str | None = None
    distance_meters: int | None = None
    estimated_pickup: datetime | None = None
    estimated_delivery: datetime | None = None
    schedule_mode: str | None = None
    stripe_checkout_session_id: str | None = None
    stripe_payment_intent_id: str | None = None
    payment_id: str | None = None
    quote_amount_cents: int | None = None
    quote_state: str | None = None
    continue_url: str | None = None
    abandoned_minutes: int | None = None
    audits: list[dict[str, Any]] = Field(default_factory=list)
    domain_events: list[dict[str, Any]] = Field(default_factory=list)


class BookingDraftAnalyticsResponse(BaseModel):
    total_drafts: int
    confirmed_drafts: int
    conversion_rate_percent: float
    abandonment_rate_percent: float
    payment_success_rate_percent: float
    avg_completion_minutes: float
    most_common_failure_step: str | None
    revenue_lost_cents: int
    recovery_rate_percent: float
    active_drafts: int
    abandoned_now: int


class BookingDraftAbandonedItem(BookingDraftAdminItem):
    abandoned_minutes: int
    last_step: str
    reason: str


class BookingDraftExtendRequest(BaseModel):
    extra_minutes: int | None = None


class BookingDraftCancelRequest(BaseModel):
    reason: str | None = None


class BookingDraftBulkRequest(BaseModel):
    draft_ids: list[str]
    action: str
    extra_minutes: int | None = None
    reason: str | None = None


class BookingDraftPaymentLinkResponse(BaseModel):
    checkout_url: str | None
    payment_id: str | None
    stripe_checkout_session_id: str | None


class RouteTemplateItem(BaseModel):
    id: str
    name: str
    template_type: str
    merchant_id: str | None = None
    zone: str | None = None
    schedule: dict[str, Any] = Field(default_factory=dict)
    stops: list[dict[str, Any]] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    created_by: str | None = None
    created_at: datetime


class RouteTemplateCreateRequest(BaseModel):
    name: str
    merchant_id: str | None = None
    zone: str | None = None
    schedule: dict[str, Any] = Field(default_factory=dict)
    stops: list[dict[str, Any]] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)


class RouteTemplateUpdateRequest(BaseModel):
    name: str | None = None
    merchant_id: str | None = None
    zone: str | None = None
    schedule: dict[str, Any] | None = None
    stops: list[dict[str, Any]] | None = None
    config: dict[str, Any] | None = None
    is_active: bool | None = None
