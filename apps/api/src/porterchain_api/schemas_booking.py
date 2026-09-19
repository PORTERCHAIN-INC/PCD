"""Booking / quote / customer portal request-response schemas (§3.2.13)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AddressInput(BaseModel):
    formatted: str
    place_id: str | None = None
    lat: float | None = None
    lng: float | None = None
    # Needed for FSA pricing. When absent the FSA is recovered from `formatted`.
    postal: str | None = None


class VisitorTrackingInput(BaseModel):
    browser: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_term: str | None = None
    utm_content: str | None = None
    referrer: str | None = None
    device: str | None = None
    location: dict[str, Any] | None = None
    landing_page: str | None = None
    from_page: str | None = None
    locale: str | None = None
    source_page: str | None = None
    page_view_count: int | None = None
    paths: list[str] | None = None
    intent: str | None = None
    guide_stage: str | None = None


class WebsitePricingSnapshot(BaseModel):
    customer_price_cad: float
    driver_payout_cad: float
    platform_margin_cad: float
    distance_km: float
    duration_minutes: float
    engine_vehicle_id: str
    breakdown: dict[str, Any]
    traffic: dict[str, Any] | None = None
    quote_engine: str = "website_v1"


class CreateQuoteRequest(BaseModel):
    anonymous_session_id: str | None = None
    visitor_session_id: str | None = None
    pickup: AddressInput
    dropoff: AddressInput
    vehicle_class: str
    package_type: str = "looseParcel"
    weight_kg: float | None = None
    dimensions: str | None = None
    declared_value_cents: int | None = None
    additional_stops: list[AddressInput] | None = None
    special_instructions: str | None = None
    scheduled_at: datetime
    schedule_mode: str = "now"
    tracking: VisitorTrackingInput | None = None
    promo_code: str | None = None
    service_type: str | None = None
    website_pricing: WebsitePricingSnapshot | None = None


class PricingLineItem(BaseModel):
    code: str
    label: str
    amount_cents: int


class QuoteResponse(BaseModel):
    quote_id: str
    state: str
    amount_cents: int
    currency: str = "cad"
    amount_display: str
    expires_at: datetime
    distance_km: float | None = None
    pricing_breakdown: list[PricingLineItem]
    vehicle_class: str
    scheduled_at: datetime
    pickup: dict[str, Any] | None = None
    dropoff: dict[str, Any] | None = None
    package_type: str | None = None
    weight_kg: float | None = None
    dimensions: str | None = None
    additional_stops: list[dict[str, Any]] | None = None
    special_instructions: str | None = None


class StartBookingRequest(BaseModel):
    quote_id: str
    email: str
    phone: str
    clerk_user_id: str
    anonymous_session_id: str | None = None
    terms_accepted: bool = False
    privacy_accepted: bool = False
    dangerous_goods_confirmed: bool = False
    consent_at: str | None = None
    checkout_channel: Literal["retail", "customer"] = "retail"


class BookingResponse(BaseModel):
    quote_id: str
    state: str
    customer_id: str
    checkout_url: str | None = None
    mock_checkout: bool = False


class PaymentRetryRequest(BaseModel):
    quote_id: str


class OrderResponse(BaseModel):
    order_id: str
    order_number: str
    tracking_number: str
    state: str
    amount_cents: int
    currency: str
    scheduled_at: datetime
    pickup: dict[str, Any]
    dropoff: dict[str, Any]
    fleetbase_order_id: str | None = None
    booking_number: str | None = None
    invoice_number: str | None = None
    company_name: str | None = None
    logo_url: str | None = None
    tracking_page_message: str | None = None


class OrderTrackingResponse(BaseModel):
    order_id: str
    tracking_number: str
    state: str
    fleetbase_order_id: str | None = None
    live_tracking: dict[str, Any] | None = None


class BookingConfirmationResponse(BaseModel):
    booking_id: str
    booking_number: str
    order_id: str
    order_number: str
    tracking_number: str
    invoice_id: str
    invoice_number: str
    receipt_number: str | None = None
    payment_reference: str | None = None
    customer_reference: str | None = None
    payment_method: str | None = None
    receipt_url: str | None = None
    tax_cents: int = 0
    state: str
    amount_cents: int
    currency: str
    scheduled_at: datetime
    pickup: dict[str, Any]
    dropoff: dict[str, Any]
    fleetbase_order_id: str | None = None
    dashboard_url: str = "http://localhost:3004/dashboard"


class BookingConfirmationStatusResponse(BaseModel):
    status: str
    confirmation: BookingConfirmationResponse | None = None


class CheckoutMockCompleteRequest(BaseModel):
    quote_id: str


class CustomerDashboardResponse(BaseModel):
    active_order: dict[str, Any] | None = None
    orders: list[dict[str, Any]] = Field(default_factory=list)
    bookings: list[dict[str, Any]] = Field(default_factory=list)
    invoices: list[dict[str, Any]] = Field(default_factory=list)
    payments: list[dict[str, Any]] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)


class CustomerSupportTicketRequest(BaseModel):
    subject: str
    description: str | None = None
    order_id: str | None = None


class CustomerSupportTicketResponse(BaseModel):
    ticket_id: str
    status: str
    subject: str
    description: str | None = None
    order_id: str | None = None
    created_at: datetime


class CustomerRebookResponse(BaseModel):
    pickup: dict[str, Any]
    dropoff: dict[str, Any]
    vehicle_class: str | None = None
    source_order_id: str
    tracking_number: str


class PaymentResponse(BaseModel):
    payment_id: str
    status: str
    amount_cents: int
    currency: str
    checkout_url: str | None = None
    failure_reason: str | None = None
    retry_count: int = 0


class CreateBookingDraftRequest(BaseModel):
    session_id: str
    pickup: AddressInput | None = None
    dropoff: AddressInput | None = None
    vehicle_class: str | None = None
    package_type: str | None = None
    weight_kg: float | None = None
    dimensions: str | None = None
    declared_value_cents: int | None = None
    additional_stops: list[AddressInput] | None = None
    special_instructions: str | None = None
    promo_code: str | None = None
    estimated_pickup: datetime | None = None
    estimated_delivery: datetime | None = None
    schedule_mode: str | None = "now"
    current_step: str | None = "details"


class UpdateBookingDraftRequest(BaseModel):
    pickup: AddressInput | None = None
    dropoff: AddressInput | None = None
    vehicle_class: str | None = None
    package_type: str | None = None
    weight_kg: float | None = None
    dimensions: str | None = None
    declared_value_cents: int | None = None
    additional_stops: list[AddressInput] | None = None
    special_instructions: str | None = None
    promo_code: str | None = None
    estimated_pickup: datetime | None = None
    estimated_delivery: datetime | None = None
    schedule_mode: str | None = None
    current_step: str | None = None


class BookingDraftAuditItem(BaseModel):
    event_label: str
    from_state: str | None
    to_state: str
    actor_type: str
    actor_id: str | None = None
    occurred_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class BookingDraftResponse(BaseModel):
    draft_id: str
    session_id: str
    customer_id: str | None = None
    quote_id: str | None = None
    state: str
    current_step: str
    payment_status: str | None = None
    pickup: dict[str, Any] | None = None
    dropoff: dict[str, Any] | None = None
    additional_stops: list[dict[str, Any]] | None = None
    vehicle_class: str | None = None
    package_type: str | None = None
    weight_kg: float | None = None
    dimensions: str | None = None
    declared_value_cents: int | None = None
    special_instructions: str | None = None
    pricing_breakdown: dict[str, Any] | None = None
    taxes_cents: int = 0
    discounts_cents: int = 0
    promo_code: str | None = None
    amount_cents: int | None = None
    currency: str = "cad"
    estimated_pickup: datetime | None = None
    estimated_delivery: datetime | None = None
    booking_id: str | None = None
    order_id: str | None = None
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    continue_url: str | None = None


class BookingDraftDetailResponse(BookingDraftResponse):
    customer_email: str | None = None
    audits: list[BookingDraftAuditItem] = Field(default_factory=list)
