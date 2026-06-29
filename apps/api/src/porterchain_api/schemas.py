from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AddressInput(BaseModel):
    formatted: str
    place_id: str | None = None
    lat: float | None = None
    lng: float | None = None


class VisitorTrackingInput(BaseModel):
    browser: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    referrer: str | None = None
    device: str | None = None
    location: dict[str, Any] | None = None


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


class StartBookingRequest(BaseModel):
    quote_id: str
    email: str
    phone: str
    clerk_user_id: str
    anonymous_session_id: str | None = None


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
    state: str
    amount_cents: int
    currency: str
    scheduled_at: datetime
    pickup: dict[str, Any]
    dropoff: dict[str, Any]
    fleetbase_order_id: str | None = None
    dashboard_url: str = "/portal/customer"


class CheckoutMockCompleteRequest(BaseModel):
    quote_id: str


class CustomerDashboardResponse(BaseModel):
    active_order: dict[str, Any] | None = None
    orders: list[dict[str, Any]] = Field(default_factory=list)
    bookings: list[dict[str, Any]] = Field(default_factory=list)
    invoices: list[dict[str, Any]] = Field(default_factory=list)
    payments: list[dict[str, Any]] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)


class PaymentResponse(BaseModel):
    payment_id: str
    status: str
    amount_cents: int
    currency: str
    checkout_url: str | None = None
    failure_reason: str | None = None
    retry_count: int = 0
