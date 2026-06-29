from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


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


class MerchantDashboardResponse(BaseModel):
    todays_orders: int
    in_transit: int
    delivered_today: int
    pending_dispatch: int
    outstanding_invoices_cents: int
    account_balance_cents: int
    monthly_spend_cents: int
    on_time_percent: float
    notifications: list[dict[str, Any]] = Field(default_factory=list)


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


class WebhookResponse(BaseModel):
    id: str
    url: str
    events: list[str]
    is_active: bool


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
    phone: str | None = None
    billing_address: dict[str, Any] | None = None
    hst_number: str | None = None
    business_number: str | None = None
    preferred_vehicles: list[str] | None = None
    delivery_zones: list[str] | None = None


class InvoiceListItem(BaseModel):
    invoice_id: str
    invoice_number: str
    order_id: str
    amount_cents: int
    currency: str
    created_at: datetime
    stripe_receipt_url: str | None = None


class ReportSummaryResponse(BaseModel):
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


class BillingStatementResponse(BaseModel):
    payment_terms: str
    outstanding_balance_cents: int
    monthly_orders: int
    monthly_spend_cents: int


class OrderTrackingResponse(BaseModel):
    order: MerchantOrderResponse
    timeline: list[dict[str, Any]]
