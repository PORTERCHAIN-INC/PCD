"""Request / response models for the public marketing endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

CALCULATOR_VEHICLES: tuple[str, ...] = ("sedan_suv", "cargo_van", "box_16")
MONTHLY_VOLUMES: dict[str, int] = {"1-20": 10, "21-100": 60, "101-500": 300, "500+": 750}
INDUSTRIES: tuple[str, ...] = (
    "shopify-merchants",
    "pharmacy",
    "labs",
    "warehouses",
    "wholesale-traders",
    "construction",
    "plumbing-electrical",
    "other",
)


class EstimateRequest(BaseModel):
    pickup_postal: str = Field(min_length=3, max_length=7)
    dropoff_postal: str = Field(min_length=3, max_length=7)
    vehicle_class: str = Field(default="sedan_suv", max_length=32)


class EstimateLine(BaseModel):
    code: str
    label: str
    amount_cents: int


class EstimateResponse(BaseModel):
    amount_cents: int
    amount_display: str
    subtotal_cents: int
    tax_cents: int
    currency: str = "CAD"
    distance_km: float | None = None
    included_km: float | None = None
    vehicle_class: str
    pickup_fsa: str
    dropoff_fsa: str
    lines: list[EstimateLine]
    basis: str = "fsa_centroid"
    disclaimer: str


class CalculatorLeadRequest(BaseModel):
    business_name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=254)
    phone: str = Field(min_length=7, max_length=32)
    industry: str = Field(max_length=40)
    monthly_volume: str = Field(max_length=16)
    marketing_consent: bool = False
    pickup_fsa: str | None = Field(default=None, max_length=7)
    dropoff_fsa: str | None = Field(default=None, max_length=7)
    vehicle_class: str | None = Field(default=None, max_length=32)
    estimate_cents: int | None = Field(default=None, ge=0, le=10_000_000)
    # Honeypot: real browsers leave this empty (field is hidden from people).
    website: str | None = Field(default=None, max_length=200)
    form_elapsed_ms: int | None = Field(default=None, ge=0)
    utm_source: str | None = Field(default=None, max_length=120)
    utm_medium: str | None = Field(default=None, max_length=120)
    utm_campaign: str | None = Field(default=None, max_length=120)
    utm_term: str | None = Field(default=None, max_length=120)
    utm_content: str | None = Field(default=None, max_length=120)
    landing_page: str | None = Field(default=None, max_length=500)
    referrer: str | None = Field(default=None, max_length=500)
    source_page: str | None = Field(default=None, max_length=200)
    visitor_id: str | None = Field(default=None, max_length=64)
    hero_variant: str | None = Field(default=None, max_length=16)


class CalculatorLeadResponse(BaseModel):
    status: str = "received"
