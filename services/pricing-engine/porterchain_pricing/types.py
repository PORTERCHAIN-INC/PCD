"""Pricing engine request/response types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from porterchain_pricing.policy import MerchantPricingPolicy
from porterchain_pricing.rate_card import RateCard, default_rate_card

if TYPE_CHECKING:
    from porterchain_pricing.gta_rate import GtaRateConfig


@dataclass(frozen=True)
class GeoPoint:
    lat: float | None = None
    lng: float | None = None
    formatted: str = ""
    # Canadian postal code when the caller has one. FSA pricing reads the first
    # three characters; when this is empty the FSA is parsed out of `formatted`.
    postal: str = ""


@dataclass(frozen=True)
class ParcelSpec:
    """
    One packed parcel on a route, for contract schedules that bill per parcel.

    `stop_index` 0 is the dropoff; n is `additional_stops[n - 1]`. Dimensions
    take the same shapes as `PricingRequest.dimensions` (cm). Unknown weight or
    size is allowed and counts as the standard tier.
    """

    stop_index: int = 0
    weight_kg: float | None = None
    dimensions: dict[str, float] | str | None = None
    #: Boxes of one item share a key (multi-box items). Price-book merchants
    #: with `multi_box_as_one_item` bill them as one unit; contracts ignore it.
    item_key: str | None = None


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
    #: Sum of parcel volumes in cm³. When set, oversize uses this instead of one box.
    volume_cm3: float | None = None
    declared_value_cents: int | None = None
    schedule_mode: str = "now"
    scheduled_at: datetime | None = None
    is_rush: bool = False
    additional_stops: list[GeoPoint] = field(default_factory=list)
    distance_meters: int | None = None
    estimated_duration_minutes: int | None = None
    routing_source: str | None = None
    wait_minutes: float = 0.0
    channel: Literal["retail", "merchant"] = "retail"
    merchant_id: str | None = None
    promo_code: str | None = None
    wallet_credit_cents: int = 0
    referral_credit_cents: int = 0
    volume_units: int = 1
    requires_liftgate: bool = False
    #: Opt-in coverage upgrade. None = merchant default (Shopify checkout can't opt in).
    coverage_upgrade: bool | None = None
    #: Item category for the coverage recommendation (electronics, jewelry, …).
    item_category: str | None = None
    # GTA matrix inputs (optional — inferred from stops/geo when omitted)
    total_pickups: int | None = None
    total_drops: int | None = None
    is_downtown: bool | None = None
    is_upper_zone: bool | None = None
    #: Parcel / carton count for compact stop banding (default 1).
    parcel_count: int = 1
    #: Per-parcel detail. Optional: contract routes split `parcel_count`,
    #: `weight_kg` and `dimensions` across the stops when it is empty.
    parcels: list[ParcelSpec] = field(default_factory=list)
    #: "parcels" or "vehicle" (whole-vehicle / dedicated booking).
    booking_mode: str = "parcels"
    #: Hours booked for a dedicated vehicle (None = the minimum units).
    dedicated_hours: float | None = None


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
    # GeoJSON ring [[lng, lat], ...] — AABB rectangles today (P2-1). Optional for DB rows.
    polygon: list[list[float]] | None = None


@dataclass
class FsaRateRecord:
    """
    A flat price for delivering into one forward sortation area.

    `merchant_id`, `origin_fsa` and `vehicle_class` are all optional filters —
    leaving one blank means "any". A single-warehouse Shopify store therefore
    needs only `dest_fsa` and `flat_cents`. The most specific matching row wins.
    """

    id: str
    dest_fsa: str
    flat_cents: int
    merchant_id: str | None = None
    origin_fsa: str | None = None
    vehicle_class: str | None = None
    #: When true the price also covers downtown / upper-zone fees, so a flat
    #: quote cannot be followed by a surprise geographic surcharge.
    includes_location_fees: bool = True
    label: str = ""
    is_active: bool = True
    config: dict[str, Any] = field(default_factory=dict)

    def specificity(self) -> int:
        """Higher wins. Merchant beats origin beats vehicle."""
        return (
            (8 if self.merchant_id else 0)
            + (4 if self.origin_fsa else 0)
            + (2 if self.vehicle_class else 0)
        )


@dataclass
class SizeWeightConfig:
    """Overweight / oversize / declared-value thresholds, in the units billed."""

    weight_threshold_kg: float = 0.0
    weight_cents_per_kg: int = 0
    volume_threshold_cm3: int = 0
    cents_per_10k_cm3: int = 0
    declared_value_threshold_cents: int = 0
    declared_value_rate: float = 0.0


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
    # GTA matrix returns a clean pre-tax quote; HST only when configured in system_config.
    hst_percent: float = 0.0
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
    rate_card: RateCard = field(default_factory=default_rate_card)
    gta_rate: GtaRateConfig | None = None
    fsa_rates: list[FsaRateRecord] = field(default_factory=list)
    #: Parsed from `merchant_pricing_config`; platform defaults when absent.
    merchant_policy: MerchantPricingPolicy | None = None
    #: Global price book (`system_config.pricing_book`, raw); None = built-in defaults (all OFF).
    price_book: dict[str, Any] | None = None
    #: Pricing settings version id stamped on every quote (e.g. "pv-3").
    price_version: str | None = None
    #: Raw ``system_config.parcel_coverage``; None = built-in defaults.
    coverage: dict[str, Any] | None = None
