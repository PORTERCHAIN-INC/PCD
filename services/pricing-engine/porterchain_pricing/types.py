"""Pricing engine request/response types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


@dataclass(frozen=True)
class GeoPoint:
    lat: float | None = None
    lng: float | None = None
    formatted: str = ""


@dataclass(frozen=True)
class PricingRequest:
    """Input for a price calculation — B2C or B2B."""

    pickup: GeoPoint
    dropoff: GeoPoint
    vehicle_class: str
    package_type: str = "looseParcel"
    service_type: str = "same_day"
    weight_kg: float | None = None
    dimensions: dict[str, float] | str | None = None
    declared_value_cents: int | None = None
    schedule_mode: str = "now"
    scheduled_at: datetime | None = None
    is_rush: bool = False
    additional_stops: list[GeoPoint] = field(default_factory=list)
    distance_meters: int | None = None
    estimated_duration_minutes: int | None = None
    channel: Literal["retail", "merchant"] = "retail"
    merchant_id: str | None = None
    promo_code: str | None = None
    wallet_credit_cents: int = 0
    referral_credit_cents: int = 0
    volume_units: int = 1


@dataclass
class PriceLineItem:
    code: str
    label: str
    amount_cents: int


@dataclass
class PriceBreakdown:
    """Structured breakdown shown to customers and admins."""

    base_cents: int = 0
    distance_cents: int = 0
    vehicle_cents: int = 0
    weight_cents: int = 0
    fuel_cents: int = 0
    tax_cents: int = 0
    discount_cents: int = 0
    subtotal_cents: int = 0
    final_cents: int = 0
    currency: str = "cad"
    items: list[PriceLineItem] = field(default_factory=list)
    zone_code: str | None = None
    contract_id: str | None = None
    promo_code: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_item(self, code: str, label: str, amount_cents: int) -> None:
        if amount_cents == 0:
            return
        self.items.append(PriceLineItem(code=code, label=label, amount_cents=amount_cents))

    def finalize(self) -> PriceBreakdown:
        charges = sum(i.amount_cents for i in self.items if i.amount_cents > 0)
        discounts = sum(-i.amount_cents for i in self.items if i.amount_cents < 0)
        self.subtotal_cents = charges - discounts
        self.final_cents = max(0, self.subtotal_cents + self.tax_cents)
        return self

@dataclass
class TariffRecord:
    id: str
    name: str
    tariff_type: str
    vehicle_class: str | None = None
    zone: str | None = None
    merchant_id: str | None = None
    base_cents: int = 0
    per_km_cents: int = 0
    fuel_surcharge_percent: float = 0.0
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class PromotionRecord:
    id: str
    code: str
    promotion_type: str = "coupon"
    discount_percent: float | None = None
    discount_cents: int | None = None
    merchant_id: str | None = None
    is_active: bool = True
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class ZoneRecord:
    code: str
    name: str
    bounds: dict[str, float]
    multiplier: float = 1.0


@dataclass
class ContractRecord:
    id: str
    merchant_id: str
    name: str
    rules: dict[str, Any] = field(default_factory=dict)
    minimum_monthly_commitment_cents: int = 0
    is_active: bool = True


@dataclass
class TaxConfig:
    hst_percent: float = 13.0
    tax_included: bool = False
    exempt_merchant_ids: list[str] = field(default_factory=list)


@dataclass
class FuelConfig:
    surcharge_percent: float = 0.0
    base_fuel_price_cents: int = 145
    current_fuel_price_cents: int = 158


@dataclass
class PricingContext:
    """Loaded rules for a calculation."""

    tariffs: list[TariffRecord] = field(default_factory=list)
    promotions: list[PromotionRecord] = field(default_factory=list)
    zones: list[ZoneRecord] = field(default_factory=list)
    contract: ContractRecord | None = None
    merchant_pricing_config: dict[str, Any] = field(default_factory=dict)
    tax: TaxConfig = field(default_factory=TaxConfig)
    fuel: FuelConfig = field(default_factory=FuelConfig)
