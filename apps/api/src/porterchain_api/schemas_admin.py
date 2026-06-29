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
    insurance_verified: bool | None = None
    vehicle_verified: bool | None = None
    background_check_status: str | None = None


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


class AssignDriverRequest(BaseModel):
    driver_id: str


class ClaimItem(BaseModel):
    id: str
    order_id: str
    claim_type: str
    status: str
    description: str | None
    created_at: datetime


class ClaimCreateRequest(BaseModel):
    order_id: str
    claim_type: str
    description: str | None = None


class TicketItem(BaseModel):
    id: str
    status: str
    priority: str
    subject: str
    order_id: str | None
    created_at: datetime


class TicketCreateRequest(BaseModel):
    subject: str
    description: str | None = None
    priority: str = "normal"
    order_id: str | None = None
    customer_id: str | None = None
    merchant_id: str | None = None
    driver_id: str | None = None


class TariffItem(BaseModel):
    id: str
    name: str
    tariff_type: str
    vehicle_class: str | None
    zone: str | None
    base_cents: int
    per_km_cents: int
    fuel_surcharge_percent: float
    is_active: bool


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


class StaffItem(BaseModel):
    id: str
    email: str
    name: str | None
    role: str
    created_at: datetime


class StaffRoleUpdateRequest(BaseModel):
    role: str


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
    discount_percent: float | None
    discount_cents: int | None
    is_active: bool


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


class PricingZoneCreateRequest(BaseModel):
    code: str
    name: str
    bounds: dict[str, float]
    multiplier: float = 1.0


class MerchantContractItem(BaseModel):
    id: str
    merchant_id: str
    name: str
    minimum_monthly_commitment_cents: int
    is_active: bool


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
