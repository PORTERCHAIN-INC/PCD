"""Admin pricing-component request/response contracts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from porterchain_pricing.types import GeoPoint


class PointInput(BaseModel):
    lat: float | None = None
    lng: float | None = None
    formatted: str = ""
    postal: str | None = None

    def to_geo(self) -> GeoPoint:
        return GeoPoint(
            lat=self.lat, lng=self.lng, formatted=self.formatted, postal=self.postal or ""
        )


class ComponentResponse(BaseModel):
    component: str
    total_cents: int
    items: list[dict[str, Any]]
    metadata: dict[str, Any]


class DistanceRequest(BaseModel):
    vehicle_type: str = "cargo_van"
    total_km: float = Field(ge=0)
    config_overrides: dict[str, Any] | None = None


class StopsRequest(BaseModel):
    vehicle_type: str = "cargo_van"
    total_pickups: int = Field(default=1, ge=1)
    total_drops: int = Field(default=1, ge=1)
    config_overrides: dict[str, Any] | None = None


class LocationRequest(BaseModel):
    pickup: PointInput | None = None
    dropoff: PointInput | None = None
    additional_stops: list[PointInput] = Field(default_factory=list)
    is_downtown: bool | None = None
    is_upper_zone: bool | None = None
    config_overrides: dict[str, Any] | None = None


class SizeWeightRequest(BaseModel):
    weight_kg: float | None = Field(default=None, ge=0)
    dimensions: dict[str, float] | str | None = None
    declared_value_cents: int | None = Field(default=None, ge=0)
    merchant_id: str | None = None


class FsaQuoteRequest(BaseModel):
    dest_fsa: str | None = None
    origin_fsa: str | None = None
    pickup: PointInput | None = None
    dropoff: PointInput | None = None
    merchant_id: str | None = None
    vehicle_class: str | None = None


class FsaRateBody(BaseModel):
    dest_fsa: str
    flat_cents: int = Field(ge=0)
    merchant_id: str | None = None
    origin_fsa: str | None = None
    vehicle_class: str | None = None
    includes_location_fees: bool = True
    label: str | None = None
    is_active: bool = True
    #: Opaque JSON — e.g. ``{"tier": "T1"}`` for schedule route minimums.
    config: dict[str, Any] | None = None


class FsaRateBulkBody(BaseModel):
    rates: list[FsaRateBody] = Field(min_length=1, max_length=500)
    merchant_id: str | None = None


class FsaRateOut(FsaRateBody):
    id: str


class SimulateQuoteRequest(BaseModel):
    """Full quote preview for Pricing Center — loads live merchant/platform context."""

    merchant_id: str | None = None
    channel: str = "merchant"
    vehicle_class: str = "cargo_van"
    distance_meters: float = Field(default=15_000, ge=0)
    use_typed_distance: bool = False
    total_pickups: int = Field(default=1, ge=1)
    total_drops: int = Field(default=1, ge=1)
    pickup: PointInput | None = None
    dropoff: PointInput | None = None
    weight_kg: float | None = None
    dimensions: dict[str, float] | str | None = None
    parcel_count: int = Field(default=1, ge=1)
    requires_liftgate: bool = False
    is_downtown: bool | None = None
    is_upper_zone: bool | None = None
    gta_rate_override: dict[str, Any] | None = None


class SimulateQuoteResponse(BaseModel):
    final_cents: int
    subtotal_cents: int
    tax_cents: int
    base_cents: int
    currency: str = "cad"
    pricing_model: str | None = None
    pricing_model_requested: str | None = None
    items: list[dict[str, Any]]
    metadata: dict[str, Any]
    what_won: str
