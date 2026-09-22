from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

BlogTag = Annotated[str, Field(max_length=40)]


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


class MerchantSizeTier(BaseModel):
    """
    One row of a merchant's size / weight surcharge table.

    Limits are kept in the unit the admin entered so the form round-trips
    exactly; conversion to cm / kg happens in the pricing engine. A null limit
    is unbounded, so a row with no limits at all is a catch-all.
    """

    surcharge_cents: int = Field(default=0, ge=0)
    label: str = ""
    max_length: float | None = Field(default=None, ge=0)
    max_width: float | None = Field(default=None, ge=0)
    max_height: float | None = Field(default=None, ge=0)
    dimension_unit: Literal["cm", "in", "ft"] = "cm"
    max_weight: float | None = Field(default=None, ge=0)
    weight_unit: Literal["kg", "lb"] = "kg"


class MerchantSurcharges(BaseModel):
    downtown: bool = True
    upper_zone: bool = True


class MerchantPricingRequest(BaseModel):
    """
    The pricing controls an admin owns for one merchant.

    Deliberately narrower than `pricing_config`: writing this must not disturb
    the contract-era keys (`custom_rules`, `volume_discounts`) that live in the
    same JSON column. `gta_rate` and `rate_card` are explicit overlays — omit
    them (`exclude_unset`) to leave stored values alone; send null to clear
    `gta_rate`.
    """

    pricing_model: Literal["distance", "fsa"] = "distance"
    surcharges: MerchantSurcharges = Field(default_factory=MerchantSurcharges)
    size_tiers: list[MerchantSizeTier] = Field(default_factory=list)
    #: Per-merchant Distance matrix overlay (CAD dollars), merged onto platform GTA.
    gta_rate: dict[str, Any] | None = None
    #: Optional RateCard surcharge knobs (liftgate, weight, extra stop, …).
    rate_card: dict[str, Any] | None = None


class MerchantPricingResponse(MerchantPricingRequest):
    merchant_id: str
    #: FSA rows targeting this merchant, so the UI can warn when a merchant is
    #: pinned to FSA pricing but has no rates of its own.
    fsa_rate_count: int = 0
    platform_fsa_rate_count: int = 0
    #: Same DTO the merchant and partner GET. Admin Pricing tab previews this.
    card: dict[str, Any] | None = None
    #: True when `pricing_config.gta_rate` is present (Distance customization).
    has_custom_gta: bool = False
    #: Platform GTA before merchant overlay — for Reset / diff in admin UI.
    platform_gta_rate: dict[str, Any] | None = None


class MerchantUpdateRequest(BaseModel):
    payment_terms: str | None = None
    pricing_config: dict[str, Any] | None = None
    credit_limit_cents: int | None = None
    parent_merchant_id: str | None = None
    support_tier: str | None = Field(default=None, pattern="^(standard|priority|enterprise)$")
    billing_cycle: str | None = Field(
        default=None, pattern="^(WEEKLY|BIWEEKLY|MONTHLY|CUSTOM)$"
    )
    preferred_vehicles: list[str] | None = None
    delivery_zones: list[str] | None = None
    service_area: str | None = None
    company_name: str | None = None
    legal_name: str | None = None
    email: str | None = None
    website: str | None = None
    industry: str | None = None
    phone: str | None = None
    hst_number: str | None = None
    business_number: str | None = None
    tax_exempt: bool | None = None
    tax_region: str | None = None
    billing_address: dict[str, Any] | None = None
    stripe_enabled: bool | None = None
    cod_enabled: bool | None = None


class MerchantInviteRequest(BaseModel):
    email: str
    role: str | None = None


class MerchantTeamRoleUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None


class MerchantCloseRequest(BaseModel):
    reason: str


class MerchantConvertRequest(BaseModel):
    owner_email: str | None = None
    write_off_ar: bool = False


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
    #: Set at create so a Shopify merchant is not born on the platform default
    #: and then patched later. Same shape as PUT /pricing.
    pricing: MerchantPricingRequest | None = None


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
    wallet_balance_cents: int
    created_at: datetime


class DriverVerifyRequest(BaseModel):
    license_verified: bool | None = None
    medical_transport_certified: bool | None = None
    insurance_verified: bool | None = None
    vehicle_verified: bool | None = None
    background_check_status: str | None = None


class DriverRejectRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class DriverDocumentDecisionRequest(BaseModel):
    doc_type: str = Field(min_length=1, max_length=64)
    decision: str = Field(pattern="^(verified|rejected|cleared)$")
    reason: str | None = Field(default=None, max_length=500)


class DriverVehicleUpdate(BaseModel):
    vehicle_class: str | None = None
    plate_number: str | None = Field(default=None, max_length=32)
    make_model: str | None = Field(default=None, max_length=128)
    capacity_kg: float | None = None
    compliance_expires_at: datetime | None = None
    is_active: bool | None = None


class DriverAddressInput(BaseModel):
    street: str | None = None
    city: str | None = None
    province: str | None = None
    postal_code: str | None = None


class DriverEmergencyContactInput(BaseModel):
    name: str | None = None
    phone: str | None = None
    relationship: str | None = None


class DriverProfilePatch(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    license_class: str | None = Field(default=None, max_length=32)
    service_area: str | None = Field(default=None, max_length=128)
    employment_type: str | None = Field(default=None, max_length=64)
    languages: list[str] | None = None
    address: DriverAddressInput | None = None
    emergency_contact: DriverEmergencyContactInput | None = None


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
    purchase_order_number: str | None = None
    cost_centre: str | None = None
    internal_reference: str | None = None
    order_source: str | None = None
    order_source_label: str | None = None
    shopify: dict[str, Any] | None = None
    is_sandbox: bool = False


class OrderListPage(BaseModel):
    items: list[OrderListItem]
    total: int
    limit: int
    offset: int


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


class AdminOrderStopInput(BaseModel):
    """Adapter-shaped stop for multi-waypoint admin order builder (P0-2 / P1-4)."""

    id: str | None = None
    type: str = Field(..., description="pickup | dropoff")
    sequence: int = 0
    formatted: str
    lat: float | None = None
    lng: float | None = None
    city: str | None = None
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None
    service_time_seconds: int | None = None
    notes: str | None = None
    pod_required: bool = False


class AdminCreateOrderRequest(BaseModel):
    merchant_id: str
    order_kind: str = Field(
        ...,
        description="single | hub_spoke | multi_pickup_delivery | scheduled_pickup",
    )
    stops: list[AdminOrderStopInput] = Field(..., min_length=2)
    vehicle_class: str = "cargoVan"
    package_type: str = "looseParcel"
    weight_kg: float | None = None
    scheduled_at: datetime
    schedule_mode: str = "now"
    special_instructions: str | None = None
    internal_reference: str | None = None


class AdminCreateOrderResponse(BaseModel):
    order_id: str
    order_number: str
    tracking_number: str
    state: str
    amount_cents: int
    currency: str = "cad"
    stop_count: int
    warnings: list[str] = Field(default_factory=list)


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
    stops: list[dict[str, Any]] = Field(default_factory=list)
    parcel_amendable: bool = False
    route_import_job_id: str | None = None
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
    status_sync: dict[str, Any] = Field(default_factory=dict)


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


class PlatformUserAuthorizeRequest(BaseModel):
    platform_user_id: str | None = None
    clerk_user_id: str | None = None
    email: str | None = None
    name: str | None = None
    reason: str | None = None


class PlatformUserAuthorizeResponse(BaseModel):
    platform_user_id: str
    user_type: str
    email: str
    role: str | None = None
    access_status: str
    modules: list[str] = Field(default_factory=list)
    actions_taken: list[str] = Field(default_factory=list)


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


class StaffEnrollResponse(BaseModel):
    """Staff IdP enrollment — activate link emailed; token still returned for ops copy."""

    admin_user_id: str
    email: str
    role: str
    enrollment_token: str | None = None
    expires_at: float
    clerk_invite: bool = False
    email_sent: bool = False
    passkeys_removed: int | None = None
    sessions_revoked: int | None = None


class SettingsConfigUpdateRequest(BaseModel):
    value: Any
    reason: str | None = None


class SettingsImportRequest(BaseModel):
    config: dict[str, Any]
    reason: str | None = None
    dry_run: bool = False


class CrmTaskCreateRequest(BaseModel):
    title: str
    lead_id: str | None = None
    merchant_id: str | None = None


class CrmNoteCreateRequest(BaseModel):
    entity_type: str
    entity_id: str
    body: str


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
    customer_id: str | None = None
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
    last_reminded_at: str | None = None
    created_at: datetime


class ApContactItem(BaseModel):
    """Who collections phones about an unpaid invoice (BL)."""

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    role: str | None = None
    is_primary: bool = False
    #: ``billing_contact`` when a named AP contact exists, else ``company``.
    source: str = "company"


class FinanceCollectionItem(FinanceInvoiceItem):
    """An open invoice plus what it takes to chase it (BL)."""

    days_overdue: int = 0
    aging_bucket: str = "Current"
    ap_contact: ApContactItem | None = None


class FinanceInvoicePage(BaseModel):
    items: list[FinanceInvoiceItem]
    total: int
    limit: int
    offset: int


class FinanceInvoiceDetailResponse(FinanceInvoiceItem):
    payment: dict[str, Any] | None = None
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    audit_log: list[dict[str, Any]] = Field(default_factory=list)
    duplicates: list[dict[str, Any]] = Field(default_factory=list)
    quote_id: str | None = None
    quote_amount_cents: int | None = None
    pricing_breakdown: dict[str, Any] | None = None
    pricing_model: str | None = None
    pricing_metadata: dict[str, Any] = Field(default_factory=dict)


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


class FinancePaymentPage(BaseModel):
    items: list[FinancePaymentItem]
    total: int
    limit: int
    offset: int


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


class MerchantArGenerateRequest(BaseModel):
    merchant_id: str
    period_start: datetime | None = None
    period_end: datetime | None = None


class MerchantArRecordPaymentRequest(BaseModel):
    amount_cents: int | None = None
    method: str = "wire"
    reference: str | None = None
    paid_at: datetime | None = None


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
    created_at: datetime | None = None


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


class AdminCustomerAddressInput(BaseModel):
    formatted: str = Field(min_length=1, max_length=512)
    place_id: str | None = None
    lat: float | None = None
    lng: float | None = None


class AdminCreateCustomerBookingDraftRequest(BaseModel):
    """Admin phone-book: create retail quote + draft for an existing customer (Stripe only)."""

    pickup: AdminCustomerAddressInput
    dropoff: AdminCustomerAddressInput
    vehicle_class: str = Field(min_length=1, max_length=64)
    package_type: str = "looseParcel"
    weight_kg: float | None = None
    dimensions: str | None = None
    declared_value_cents: int | None = None
    special_instructions: str | None = None
    scheduled_at: datetime
    schedule_mode: str = "now"
    send_payment_link: bool = False


class AdminCreateCustomerBookingDraftResponse(BaseModel):
    draft_id: str
    draft_number: str | None = None
    quote_id: str
    customer_id: str
    amount_cents: int
    currency: str = "cad"
    state: str
    checkout_url: str | None = None
    payment_id: str | None = None
    stripe_checkout_session_id: str | None = None


class BlogPostItem(BaseModel):
    id: str
    slug: str
    locale: str
    title: str
    description: str
    body_md: str = ""
    category: str
    author_id: str
    status: str
    featured: bool = False
    trending: bool = False
    case_study: bool = False
    on_time_percent: str | None = None
    cost_delta_percent: str | None = None
    volume_metric: str | None = None
    tags: list[str] = Field(default_factory=list)
    cover_image_url: str | None = None
    published_at: str | None = None
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime


class BlogPostCreateRequest(BaseModel):
    slug: str = Field(min_length=2, max_length=160)
    locale: str = Field(min_length=2, max_length=8)
    title: str = Field(min_length=1, max_length=512)
    description: str = Field(default="", max_length=4000)
    body_md: str = Field(default="", max_length=100_000)
    category: str = Field(default="logistics", max_length=64)
    author_id: str = Field(default="porterchain", max_length=64)
    status: str = Field(default="draft", max_length=32)
    featured: bool = False
    trending: bool = False
    case_study: bool = False
    on_time_percent: str | None = Field(default=None, max_length=32)
    cost_delta_percent: str | None = Field(default=None, max_length=32)
    volume_metric: str | None = Field(default=None, max_length=128)
    tags: list[BlogTag] = Field(default_factory=list, max_length=32)
    cover_image_url: str | None = Field(default=None, max_length=1024)
    published_at: date | None = None


class BlogPostUpdateRequest(BaseModel):
    slug: str | None = Field(default=None, min_length=2, max_length=160)
    locale: str | None = Field(default=None, min_length=2, max_length=8)
    title: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = Field(default=None, max_length=4000)
    body_md: str | None = Field(default=None, max_length=100_000)
    category: str | None = Field(default=None, max_length=64)
    author_id: str | None = Field(default=None, max_length=64)
    status: str | None = Field(default=None, max_length=32)
    featured: bool | None = None
    trending: bool | None = None
    case_study: bool | None = None
    on_time_percent: str | None = Field(default=None, max_length=32)
    cost_delta_percent: str | None = Field(default=None, max_length=32)
    volume_metric: str | None = Field(default=None, max_length=128)
    tags: list[BlogTag] | None = Field(default=None, max_length=32)
    cover_image_url: str | None = Field(default=None, max_length=1024)
    clear_cover_image_url: bool = False
    published_at: date | None = None
    clear_published_at: bool = False


class BoardMoveBody(BaseModel):
    order_id: str
    to_column: str
    reason: str | None = None


class ExceptionResolveBody(BaseModel):
    note: str | None = None


class OptimizeRunBody(BaseModel):
    order_ids: list[str] | None = None
    mode: str = "allocate"
    engine: str | None = "vroom"
    #: Input shaping only — never a second solver. ``fleet`` = all synced;
    #: ``merchant`` = one merchant's orders; ``vehicle`` = lock vehicle_ids.
    shape: str = "fleet"
    merchant_id: str | None = None
    vehicle_ids: list[str] | None = None
    driver_ids: list[str] | None = None


class OptimizeCommitBody(BaseModel):
    assignments: list[dict]
    scheduled_date: str | None = None
    #: Idempotent commit key — retries with the same run_id return the prior result.
    run_id: str | None = None
    #: Optional driver sequence CAS — 409 when another apply won the race.
    expected_sequence_version: int | None = None
    pc_driver_id: str | None = None


class CopilotActionBody(BaseModel):
    action_id: str
    order_id: str
    driver_id: str | None = None
    reason: str | None = None


class CopilotLlmSuggestBody(BaseModel):
    """Read-only LLM ops assist (NVIDIA NIM when configured). Not on pay path."""

    context: str = Field(min_length=1, max_length=8000)
    enable_intelligence: bool = True
    merchant_id: str | None = Field(default=None, max_length=36)
    include_sla_queue: bool = True


class DriverActionRequest(BaseModel):
    type: str
    message: str | None = None


class DriverPayoutCreateRequest(BaseModel):
    amount_cents: int | None = None
    reference: str | None = None


class VisitorIntelligenceResponse(BaseModel):
    session_id: str | None = None
    intent_score: int | None = None
    touch_count: int | None = None
    quote_generated: bool | None = None
    last_quote_id: str | None = None
    customer_id: str | None = None
    device: str | None = None
    attribution: dict[str, Any] = Field(default_factory=dict)
    signals: dict[str, Any] = Field(default_factory=dict)
    quotes: list[dict[str, Any]] = Field(default_factory=list)
    guide: dict[str, Any] | None = None


class ReportsRequest(BaseModel):
    write_files: bool = False
