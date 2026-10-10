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
    # Needed for FSA pricing. Shopify sends this on every order; when it is
    # absent the FSA is recovered from `formatted`.
    postal: str | None = None


class MerchantBookDeliveryRequest(BaseModel):
    pickup: AddressInput
    dropoff: AddressInput
    additional_stops: list[AddressInput] | None = None
    vehicle_class: str = "cargo_van"
    package_type: str = "looseParcel"
    weight_kg: float | None = None
    dimensions: str | None = None
    scheduled_at: datetime
    schedule_mode: str = "now"
    special_instructions: str | None = None
    site_access_notes: str | None = Field(
        default=None,
        description="Gate code, liftgate, foreman contact — jobsite delivery (§8.1.6)",
    )
    requires_liftgate: bool = Field(
        default=False,
        description="Liftgate required at delivery — adds construction surcharge (§8.1.7)",
    )
    declared_value_cents: int | None = Field(default=None, ge=0, description="Declared value of the goods (cents)")
    coverage_upgrade: bool | None = Field(
        default=None, description="Upgrade cover to $25,000 (+$10). None = merchant default."
    )
    item_category: str | None = Field(default=None, description="Item category, e.g. electronics")
    custodian_name: str | None = Field(default=None, description="Medical chain-of-custody custodian (§8.1.2)")
    specimen_id: str | None = Field(default=None, description="Medical specimen / requisition ID (§8.1.2)")
    seal_number: str | None = Field(default=None, description="Tamper seal number (§8.1.2)")
    requires_cold_chain: bool = Field(default=False, description="Refrigerated transport required (§8.1.9)")
    temperature_min_c: float | None = Field(default=None, description="Cold-chain minimum °C (§8.1.9)")
    temperature_max_c: float | None = Field(default=None, description="Cold-chain maximum °C (§8.1.9)")
    delivery_window_start: datetime | None = Field(default=None, description="Food delivery window start (§8.1.8)")
    delivery_window_end: datetime | None = Field(default=None, description="Food delivery window end (§8.1.8)")
    pickup_window_start: datetime | None = Field(
        default=None, description="Ready-from for pickup (America/Toronto in the portal)"
    )
    pickup_window_end: datetime | None = Field(
        default=None, description="Pickup-by time — last moment the driver should collect"
    )
    packages: list["RouteImportPackageInput"] | None = None
    internal_reference: str | None = None
    purchase_order_number: str | None = None
    cost_centre: str | None = None
    recipient_id: str | None = None
    consignee_email: str | None = None
    saved_pickup_id: str | None = None
    template_id: str | None = None
    is_recurring: bool = False
    recurrence_rule: str | None = None
    #: Cash-on-delivery amount (cents). Requires merchant.cod_enabled + Connect.
    cod_amount_cents: int | None = Field(default=None, ge=0)
    otp_required: bool = Field(
        default=False,
        description="Require a delivery OTP from the receiver before Complete POD",
    )
    #: When true, create a test order (no dispatch / live side-effects).
    is_sandbox: bool = False


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
    #: MapsService label — valhalla | osrm | haversine. Never google. Top-level so
    #: clients can assert engine without reading vendor keys inside breakdown.
    routing_source: str | None = None
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
    is_sandbox: bool = False
    public_track_url: str | None = None
    consignee_email: str | None = None
    consignee_emailed: bool = False


class MerchantTrackingEmailRequest(BaseModel):
    email: str | None = None


class MerchantTrackingEmailResponse(BaseModel):
    sent: bool
    email: str
    public_track_url: str | None = None


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


class MerchantStandingOrderCreateRequest(BaseModel):
    booking_template_id: str
    recurrence_rule: str = "weekly"
    next_run_at: datetime | None = None


class MerchantStandingOrderResponse(BaseModel):
    id: str
    merchant_id: str
    booking_template_id: str
    template_name: str | None = None
    recurrence_rule: str
    next_run_at: datetime
    last_run_at: datetime | None = None
    last_order_id: str | None = None
    last_error: str | None = None
    is_active: bool
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
    on_time_percent: float | None = None
    delivery_success_percent: float | None = None
    payment_terms: str
    pending_dispatch: int = 0
    outstanding_invoices_cents: int = 0
    account_balance_cents: int = 0
    performance_charts: DashboardPerformanceCharts = Field(default_factory=DashboardPerformanceCharts)
    recent_deliveries: list[DashboardDeliveryItem] = Field(default_factory=list)
    recent_activity: list[DashboardActivityItem] = Field(default_factory=list)
    notifications: list[DashboardNotificationItem] = Field(default_factory=list)
    latest_invoice: DashboardInvoiceLink | None = None
    completeness: dict[str, Any] | None = None


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
    cost_centre: str | None = None
    is_sandbox: bool = False
    created_at: datetime


class SavedAddressResponse(BaseModel):
    id: str
    label: str
    address_type: str
    formatted: str
    is_default: bool
    postal: str | None = None
    lat: float | None = None
    lng: float | None = None


class RecipientResponse(BaseModel):
    id: str
    name: str
    email: str | None
    phone: str | None
    company: str | None
    default_address: dict[str, Any] | None = None


class BulkUploadResponse(BaseModel):
    job_id: str
    status: str
    total_rows: int
    valid_rows: int
    error_rows: int
    duplicate_rows: int
    preview: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    warnings: list[dict[str, Any]] = []


class RouteImportPackageInput(BaseModel):
    """Per-stop parcel. Stored on the import job and copied to order compliance stops."""

    id: str | None = None
    name: str | None = None
    sku: str | None = None
    quantity: int | None = 1
    weight_kg: float | None = None
    length_cm: float | None = None
    width_cm: float | None = None
    height_cm: float | None = None
    dimensions: str | None = None
    notes: str | None = None
    package_type: str | None = None
    #: Multi-box items: boxes of one item share `item_key` ("box n of N" on labels).
    item_key: str | None = Field(default=None, max_length=64)
    item_label: str | None = Field(default=None, max_length=120)
    box_index: int | None = Field(default=None, ge=1, le=50)
    box_count: int | None = Field(default=None, ge=1, le=50)
    #: Shorthand: this one item ships in N boxes (expanded to N packages).
    boxes: int | None = Field(default=None, ge=1, le=50)


MerchantBookDeliveryRequest.model_rebuild()


class RouteImportStopInput(BaseModel):
    sequence: int | None = None
    stop_type: str | None = None
    address: str
    unit: str | None = None
    city: str | None = None
    province: str | None = None
    postal: str | None = None
    lat: float | None = None
    lng: float | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    external_ref: str | None = None
    notes: str | None = None
    packages: list[RouteImportPackageInput] | None = None


class RouteImportCreateRequest(BaseModel):
    schema_version: str = "route_import.v1"
    source: str = "api"
    idempotency_key: str | None = None
    vehicle_class: str = "cargo_van"
    scheduled_at: datetime | None = None
    package_type: str = "looseParcel"
    internal_reference: str | None = None
    cost_centre: str | None = None
    weight_kg: float | None = None
    dimensions: str | None = Field(default=None, max_length=4000)
    requires_liftgate: bool = False
    site_access_notes: str | None = None
    stops: list[RouteImportStopInput]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "schema_version": "route_import.v1",
                    "source": "agent",
                    "idempotency_key": "agent-run-2026-08-07-001",
                    "vehicle_class": "sprinter_van",
                    "scheduled_at": "2026-08-07T09:00:00-04:00",
                    "stops": [
                        {
                            "sequence": 1,
                            "stop_type": "pickup",
                            "address": "100 King St W Unit 1200, Toronto, ON M5X 1A9",
                        },
                        {
                            "sequence": 2,
                            "stop_type": "drop",
                            "address": "200 Bay St, Toronto, ON M5J 2J2",
                        },
                        {
                            "sequence": 3,
                            "stop_type": "drop",
                            "address": "1 Dundas St E, Toronto, ON M5B 2R8",
                        },
                    ],
                }
            ]
        }
    }


class RouteImportMappingField(BaseModel):
    canonical: str
    source: str | None = None
    confidence: float | None = None
    evidence: str | None = None


class RouteImportMappingPatch(BaseModel):
    mapping: list[RouteImportMappingField]


class RouteImportStopPatch(BaseModel):
    address: str | None = None
    unit: str | None = None
    city: str | None = None
    province: str | None = None
    postal: str | None = None
    lat: float | None = None
    lng: float | None = None
    stop_type: str | None = None
    notes: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    packages: list[RouteImportPackageInput] | None = None


class RouteImportResponse(BaseModel):
    schema_version: str
    job_id: str
    status: str
    source: str | None = None
    vehicle_class: str | None = None
    scheduled_at: str | datetime | None = None
    mapping: list[dict[str, Any]] = Field(default_factory=list)
    headers: list[str] = Field(default_factory=list)
    mapping_profile_id: str | None = None
    mapping_profile_name: str | None = None
    optimized: bool = False
    optimize_status: str = "idle"
    stops: list[dict[str, Any]] = Field(default_factory=list)
    quote: dict[str, Any] | None = None
    route_geometry: dict[str, Any] | None = None
    route_explanation: str | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)
    order_ids: list[str] = Field(default_factory=list)
    order_id: str | None = None
    order_state: str | None = None
    assigned_driver_id: str | None = None
    parcel_amendable: bool = False
    filename: str | None = None
    total_rows: int = 0
    valid_rows: int = 0
    error_rows: int = 0
    geocode: str = "ready"


class OrderParcelStopInput(BaseModel):
    sequence: int | None = None
    stop_type: str | None = None
    address: str | None = None
    formatted: str | None = None
    unit: str | None = None
    city: str | None = None
    province: str | None = None
    postal: str | None = None
    lat: float | None = None
    lng: float | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    notes: str | None = None
    packages: list[RouteImportPackageInput] | None = None


class OrderParcelsPatchRequest(BaseModel):
    stops: list[OrderParcelStopInput] = Field(min_length=2)
    vehicle_class: str | None = None


class OrderParcelsPatchResponse(BaseModel):
    order_id: str
    state: str
    amount_cents: int
    quote: dict[str, Any] | None = None
    stops: list[dict[str, Any]] = Field(default_factory=list)
    parcel_amendable: bool = False


class RouteImportProfileSaveRequest(BaseModel):
    name: str = "Default"


class RouteImportProfileApplyRequest(BaseModel):
    profile_id: str


class RouteImportProfileResponse(BaseModel):
    id: str
    name: str
    headers: list[str] = Field(default_factory=list)
    mapping: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str | None = None


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
    # Rotated keys keep working until this time; past it they read inactive (same as admin).
    expires_at: datetime | None = None


class WebhookCreateRequest(BaseModel):
    url: str
    events: list[str] = Field(default_factory=lambda: ["order.booked", "order.delivered"])
    environment: str = Field(default="sandbox", pattern="^(sandbox|production)$")


class WebhookUpdateRequest(BaseModel):
    url: str | None = None
    events: list[str] | None = None
    is_active: bool | None = None
    environment: str | None = Field(default=None, pattern="^(sandbox|production)$")


class WebhookResponse(BaseModel):
    id: str
    url: str
    events: list[str]
    environment: str = "production"
    is_active: bool
    created_at: datetime | None = None
    signing_secret: str | None = None


class MerchantSandboxRequest(BaseModel):
    sandbox_mode: bool


class MerchantSandboxPurgeRequest(BaseModel):
    confirm: str = Field(description='Type "PURGE TEST" to cancel undispatched sandbox orders')


class MerchantSandboxSimulateRequest(BaseModel):
    order_id: str
    deliver_webhooks: bool = True
    until_state: str | None = None


class NetSuiteConnectRequest(BaseModel):
    account_id: str = Field(min_length=2, max_length=64)


class NetSuiteSyncRequest(BaseModel):
    external_id: str
    tranid: str | None = None
    purchase_order: str | None = None
    subsidiary: str | None = None
    memo: str | None = None
    ship_date: datetime
    ship_address: dict[str, Any]
    pickup_address: dict[str, Any]
    weight_kg: float | None = None
    vehicle_class: str | None = None
    package_type: str | None = None


class MerchantApiKeyRateLimitRequest(BaseModel):
    rate_limit_per_minute: int = Field(ge=10, le=600)


class MerchantConsoleRequest(BaseModel):
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)


class MerchantCoverageZone(BaseModel):
    code: str
    name: str


class MerchantAssignedVehicle(BaseModel):
    id: str
    label: str


class MerchantCoverage(BaseModel):
    service_area: str
    service_area_note: str
    delivery_zones: list[MerchantCoverageZone] = Field(default_factory=list)
    assigned_vehicles: list[MerchantAssignedVehicle] = Field(default_factory=list)
    assigned_vehicle_ids: list[str] = Field(default_factory=list)
    coverage_note: str


class MerchantProfileResponse(BaseModel):
    id: str
    status: str
    company_name: str
    legal_name: str | None
    email: str
    phone: str | None
    website: str | None = None
    industry: str | None = None
    payment_terms: str
    billing_cycle: str | None = None
    hst_number: str | None
    business_number: str | None
    billing_address: dict[str, Any] | None
    preferred_vehicles: list[str] | None
    delivery_zones: list[str] | None
    identity_meta: dict[str, Any] | None = None
    coverage: MerchantCoverage | None = None
    cod_enabled: bool = False
    stripe_connect_account_id: str | None = None


class MerchantProfileUpdateRequest(BaseModel):
    company_name: str | None = None
    legal_name: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    industry: str | None = None
    billing_address: dict[str, Any] | None = None
    hst_number: str | None = None
    business_number: str | None = None
    tax_exempt: bool | None = None
    tax_region: str | None = None
    # preferred_vehicles / delivery_zones / service_area are admin-owned; ignored if sent.


class InvoiceListItem(BaseModel):
    invoice_id: str
    invoice_number: str
    order_id: str | None = None
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
    last_reminded_at: str | None = None
    created_at: datetime
    pdf_url: str | None = None
    stripe_receipt_url: str | None = None


class InvoiceDetailLine(BaseModel):
    line_id: str | None = None
    order_id: str | None = None
    order_number: str | None = None
    tracking_number: str | None = None
    description: str
    amount_cents: int
    tax_cents: int = 0
    channel: str | None = None
    pricing_model: str | None = None
    quote_breakdown: dict[str, Any] | None = None
    rate_quote_id: str | None = None
    rate_quote_cents: int | None = None


class InvoiceDetailResponse(BaseModel):
    invoice_id: str
    invoice_number: str
    status: str
    payment_terms: str
    due_date: str | None = None
    aging_bucket: str | None = None
    amount_cents: int
    tax_cents: int = 0
    fees_cents: int = 0
    outstanding_cents: int
    currency: str
    created_at: datetime
    pdf_url: str | None = None
    lines: list[InvoiceDetailLine] = Field(default_factory=list)
    remittance_memo: str | None = None


class MerchantPaymentItem(BaseModel):
    payment_id: str
    order_id: str | None = None
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


class MerchantRateCardVehicle(BaseModel):
    id: str
    label: str
    base_cents: int
    extra_km_cents: int
    extra_pickup_cents: int
    extra_drop_cents: int


class MerchantRateCardResponse(BaseModel):
    """Read-only commercial card. Driver payout fields never appear here."""

    pricing_model: str
    what_wins: str
    vehicles: list[MerchantRateCardVehicle] = Field(default_factory=list)
    included_km: float = 20.0
    size_tiers: list[dict[str, Any]] = Field(default_factory=list)
    surcharges: dict[str, Any] = Field(default_factory=dict)
    liftgate_cents: int = 0
    fuel_surcharge_percent: float = 0.0
    #: Merchant schedule defaults (fuel override, FSA miss, pickup, mins, compact).
    schedule: dict[str, Any] = Field(default_factory=dict)
    tax: dict[str, Any] = Field(default_factory=dict)
    weight: dict[str, Any] = Field(default_factory=dict)
    fsa_rate_count: int = 0
    platform_fsa_rate_count: int = 0
    currency: str = "cad"


class BillingStatementResponse(BaseModel):
    payment_terms: str
    billing_cycle: str = "MONTHLY"
    net_terms_days: int = 30
    outstanding_balance_cents: int
    outstanding_invoices_cents: int = 0
    uninvoiced_orders_cents: int = 0
    credit_notes_cents: int = 0
    monthly_orders: int
    monthly_spend_cents: int
    period_start: str | None = None
    period_end: str | None = None


class BillingGlossaryItem(BaseModel):
    term: str
    meaning: str


class BillingRemittance(BaseModel):
    payee: str
    advice_email: str | None = None
    memo: str
    open_invoice_numbers: list[str] = Field(default_factory=list)
    outstanding_cents: int = 0
    credits_applied_cents: int = 0
    net_terms_days: int = 30
    instructions: str
    # Interac e-Transfer: where to send and the PC-XXXXX codes to put in the message.
    method: str = "interac"
    etransfer_email: str | None = None
    open_references: list[str] = Field(default_factory=list)


class MerchantBillingOverviewResponse(BillingStatementResponse):
    billing_cycles_available: list[str] = Field(default_factory=list)
    credit_limit_cents: int | None = None
    available_credit_cents: int | None = None
    headroom_cents: int | None = None
    credits_applied_cents: int = 0
    credit_balance_cents: int = 0
    glossary: list[BillingGlossaryItem] = Field(default_factory=list)
    remittance: BillingRemittance | None = None
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
    role_label: str = ""
    is_active: bool
    seat_status: str = "active"
    created_at: datetime


class TeamInviteRequest(BaseModel):
    email: str
    role: str = "merchant_ops"


class TeamRoleUpdateRequest(BaseModel):
    role: str | None = None
    is_active: bool | None = None


class TeamMemberUpdateRequest(BaseModel):
    role: str | None = None
    is_active: bool | None = None


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
    is_primary: bool | None = None


class BillingContactPatchRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    role: str | None = None
    is_primary: bool | None = None


class WarehouseRequest(BaseModel):
    name: str
    formatted: str
    lat: float | None = None
    lng: float | None = None
    postal: str | None = None
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
    order_id: str | None = None
    order_number: str | None = None
    claim_type: str
    description: str | None = None


class SavedAddressCreateRequest(BaseModel):
    label: str
    address_type: str = "pickup"
    formatted: str
    place_id: str | None = None
    lat: float | None = None
    lng: float | None = None
    postal: str | None = None
    is_default: bool = False


class SavedAddressUpdateRequest(BaseModel):
    label: str | None = None
    address_type: str | None = None
    formatted: str | None = None
    place_id: str | None = None
    lat: float | None = None
    lng: float | None = None
    postal: str | None = None
    is_default: bool | None = None


class RecipientCreateRequest(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    default_address: dict[str, Any] | None = None


class RecipientUpdateRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    default_address: dict[str, Any] | None = None


class ReportSummaryResponse(BaseModel):
    monthly_orders: int
    monthly_spend_cents: int
    delivery_success_percent: float | None = None
    on_time_percent: float | None = None
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


class MerchantLabelsBulkRequest(BaseModel):
    order_ids: list[str]


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
    consignee_email: str | None = None
    cancel_allowed: bool = False
    cancel_rule: str | None = None


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
    display_state: str | None = None
    scheduled_at: str | None = None
    pickup: dict[str, Any] | None = None
    dropoff: dict[str, Any] | None = None
    driver: dict[str, Any] | None = None
    vehicle: dict[str, Any] | None = None
    driver_location: dict[str, Any] | None = None
    eta: dict[str, Any] | None = None
    optimized_route: dict[str, Any] | None = None
    delivery_status: dict[str, Any] | None = None
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    tracking_history: list[dict[str, Any]] = Field(default_factory=list)
    replay: list[dict[str, Any]] = Field(default_factory=list)
    proof_of_delivery: dict[str, Any] = Field(default_factory=dict)
    geofences: list[dict[str, Any]] = Field(default_factory=list)
    notifications: list[dict[str, Any]] = Field(default_factory=list)
    public_track_url: str | None = None
    branding: dict[str, Any] | None = None
    last_updated: str | None = None


class ShopifyLinkRequest(BaseModel):
    link_token: str = Field(min_length=16, max_length=4096)


class ShopifyConnectRequest(BaseModel):
    shop_domain: str
    admin_access_token: str
    webhook_secret: str | None = None
    default_pickup_address_id: str | None = None


class ShopifyPickupRequest(BaseModel):
    address_id: str = Field(min_length=1)


class ShopifyGoLiveRequest(BaseModel):
    shop_id: str | None = None
    pickup_address_id: str | None = None


class PrivacyDeleteRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class MerchantReturnSummary(BaseModel):
    """A return pickup (customer -> merchant) linked to an original order."""

    order_id: str
    tracking_number: str | None = None
    state: str
    source: str | None = None
    created_at: str | None = None
    pricing_note: str | None = None
    price_cents: int | None = None


class MerchantReturnsResponse(BaseModel):
    returns: list[MerchantReturnSummary]
