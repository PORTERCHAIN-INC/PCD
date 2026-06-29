"""Core pricing calculation engine."""

from __future__ import annotations

import re

from porterchain_pricing.catalog import (
    DECLARED_VALUE_RATE,
    DECLARED_VALUE_THRESHOLD_CENTS,
    DIMENSION_CENTS_PER_10K_CM3,
    DIMENSION_VOLUME_THRESHOLD_CM3,
    EXTRA_STOP_CENTS,
    PACKAGE_SURCHARGE_CENTS,
    RUSH_SURCHARGE_CENTS,
    SCHEDULED_SURCHARGE_CENTS,
    SERVICE_SURCHARGE_CENTS,
    VEHICLE_BASE_CENTS_PER_KM,
    VEHICLE_MINIMUM_CENTS,
    VEHICLE_SURCHARGE_CENTS,
    WEIGHT_CENTS_PER_KG,
    WEIGHT_THRESHOLD_KG,
)
from porterchain_pricing.contract import ContractService
from porterchain_pricing.distance import estimate_duration_minutes, total_route_meters
from porterchain_pricing.promotion import PromotionService
from porterchain_pricing.tax import TaxService
from porterchain_pricing.types import PriceBreakdown, PricingContext, PricingRequest
from porterchain_pricing.zone import ZoneService


class PricingEngine:
    """Retail + merchant price calculation — Fleetbase never involved."""

    def __init__(self) -> None:
        self.zones = ZoneService()
        self.contracts = ContractService()
        self.promotions = PromotionService()
        self.tax = TaxService()

    def calculate(self, request: PricingRequest, ctx: PricingContext | None = None) -> PriceBreakdown:
        ctx = ctx or PricingContext()
        breakdown = PriceBreakdown()

        distance_meters = request.distance_meters
        if distance_meters is None:
            distance_meters = total_route_meters(request.pickup, request.dropoff, request.additional_stops)
        distance_km = max((distance_meters or 5000) / 1000.0, 1.0)

        duration = request.estimated_duration_minutes or estimate_duration_minutes(distance_meters)
        breakdown.metadata["distance_meters"] = distance_meters
        breakdown.metadata["estimated_duration_minutes"] = duration

        zone_svc = self.zones.with_context(ctx)
        zone_code, zone_mult = zone_svc.zone_multiplier(request.pickup, request.dropoff)
        lane_code = zone_svc.resolve_lane(request.pickup, request.dropoff, ctx)
        breakdown.zone_code = zone_code

        vehicle = request.vehicle_class if request.vehicle_class in VEHICLE_BASE_CENTS_PER_KM else "cargoVan"

        if request.channel == "merchant" and (ctx.contract or ctx.merchant_pricing_config or ctx.tariffs):
            self.contracts.apply_contract(
                request, ctx, breakdown, distance_km=distance_km, zone_code=zone_code, lane_code=lane_code
            )

        if breakdown.base_cents == 0:
            self._apply_retail_base(request, breakdown, vehicle=vehicle, distance_km=distance_km, zone_mult=zone_mult)

        self._apply_vehicle_charge(request, breakdown, vehicle)
        self._apply_package_and_service(request, breakdown)
        self._apply_weight_and_dimensions(request, breakdown)
        self._apply_declared_value(request, breakdown)
        self._apply_schedule_and_rush(request, breakdown)
        self._apply_extra_stops(request, breakdown)
        self._apply_fuel_surcharge(ctx, breakdown)

        breakdown.subtotal_cents = sum(i.amount_cents for i in breakdown.items)
        self._apply_minimum(request, ctx, breakdown, vehicle)

        breakdown.subtotal_cents = sum(i.amount_cents for i in breakdown.items)
        self.promotions.apply(request, ctx, breakdown)
        breakdown.subtotal_cents = sum(i.amount_cents for i in breakdown.items)

        tax_svc = self.tax.with_context(ctx)
        breakdown.tax_cents = tax_svc.calculate(request, breakdown)
        return breakdown.finalize()

    def _apply_retail_base(
        self,
        request: PricingRequest,
        breakdown: PriceBreakdown,
        *,
        vehicle: str,
        distance_km: float,
        zone_mult: float,
    ) -> None:
        distance_charge = int(distance_km * VEHICLE_BASE_CENTS_PER_KM[vehicle] * zone_mult)
        minimum = int(VEHICLE_MINIMUM_CENTS[vehicle] * zone_mult)
        base = max(distance_charge, minimum)
        breakdown.base_cents = base
        breakdown.distance_cents = distance_charge
        breakdown.add_item("base", f"{vehicle} delivery", base)

    def _apply_vehicle_charge(self, request: PricingRequest, breakdown: PriceBreakdown, vehicle: str) -> None:
        surcharge = VEHICLE_SURCHARGE_CENTS.get(vehicle, 0)
        if surcharge:
            breakdown.vehicle_cents = surcharge
            breakdown.add_item("vehicle", f"Vehicle ({vehicle})", surcharge)

    def _apply_package_and_service(self, request: PricingRequest, breakdown: PriceBreakdown) -> None:
        pkg = PACKAGE_SURCHARGE_CENTS.get(request.package_type, 0)
        if pkg:
            breakdown.add_item("package", f"Package ({request.package_type})", pkg)

        svc = SERVICE_SURCHARGE_CENTS.get(request.service_type, 0)
        if svc:
            label = f"Service ({request.service_type})"
            breakdown.add_item("service", label, svc)

    def _apply_weight_and_dimensions(self, request: PricingRequest, breakdown: PriceBreakdown) -> None:
        if request.weight_kg and request.weight_kg > WEIGHT_THRESHOLD_KG:
            extra = int((request.weight_kg - WEIGHT_THRESHOLD_KG) * WEIGHT_CENTS_PER_KG)
            breakdown.weight_cents = extra
            breakdown.add_item("weight", "Weight surcharge", extra)

        volume = self._parse_volume_cm3(request.dimensions)
        if volume and volume > DIMENSION_VOLUME_THRESHOLD_CM3:
            extra = int(((volume - DIMENSION_VOLUME_THRESHOLD_CM3) / 10_000) * DIMENSION_CENTS_PER_10K_CM3)
            if extra:
                breakdown.add_item("dimensions", "Oversize dimensions", extra)

    def _apply_declared_value(self, request: PricingRequest, breakdown: PriceBreakdown) -> None:
        if request.declared_value_cents and request.declared_value_cents > DECLARED_VALUE_THRESHOLD_CENTS:
            insurance = int(request.declared_value_cents * DECLARED_VALUE_RATE)
            breakdown.add_item("declared_value", "Declared value coverage", insurance)

    def _apply_schedule_and_rush(self, request: PricingRequest, breakdown: PriceBreakdown) -> None:
        if request.is_rush or request.schedule_mode == "now":
            if request.service_type != "express":
                breakdown.add_item("rush", "Rush delivery", RUSH_SURCHARGE_CENTS)
        elif request.schedule_mode == "later" or request.service_type == "scheduled":
            breakdown.add_item("scheduled", "Scheduled delivery", SCHEDULED_SURCHARGE_CENTS)

    def _apply_extra_stops(self, request: PricingRequest, breakdown: PriceBreakdown) -> None:
        count = len(request.additional_stops)
        if count:
            amount = count * EXTRA_STOP_CENTS
            breakdown.add_item("additional_stops", f"Extra stops ({count})", amount)

    def _apply_fuel_surcharge(self, ctx: PricingContext, breakdown: PriceBreakdown) -> None:
        chargeable = breakdown.base_cents + breakdown.distance_cents + breakdown.vehicle_cents + breakdown.weight_cents
        chargeable += sum(
            i.amount_cents for i in breakdown.items if i.code in ("package", "service", "rush", "scheduled", "additional_stops")
        )
        pct = ctx.fuel.surcharge_percent
        if pct and chargeable > 0:
            fuel = int(chargeable * pct / 100)
            breakdown.fuel_cents = fuel
            breakdown.add_item("fuel", f"Fuel surcharge ({pct}%)", fuel)

    def _apply_minimum(self, request: PricingRequest, ctx: PricingContext, breakdown: PriceBreakdown, vehicle: str) -> None:
        minimum = VEHICLE_MINIMUM_CENTS.get(vehicle, 3499)
        contract_min = None
        if request.channel == "merchant":
            if ctx.contract and ctx.contract.minimum_monthly_commitment_cents:
                contract_min = int(ctx.contract.rules.get("minimum_charge_cents", minimum))
            cfg_min = ctx.merchant_pricing_config.get("minimum_charge_cents")
            if cfg_min is not None:
                contract_min = int(cfg_min)
        floor = contract_min if contract_min is not None else minimum
        if breakdown.subtotal_cents < floor:
            top_up = floor - breakdown.subtotal_cents
            breakdown.add_item("minimum", "Minimum charge", top_up)

    @staticmethod
    def _parse_volume_cm3(dimensions: dict[str, float] | str | None) -> float | None:
        if dimensions is None:
            return None
        if isinstance(dimensions, dict):
            l = float(dimensions.get("length_cm") or dimensions.get("l") or 0)
            w = float(dimensions.get("width_cm") or dimensions.get("w") or 0)
            h = float(dimensions.get("height_cm") or dimensions.get("h") or 0)
            if l and w and h:
                return l * w * h
            return None
        match = re.findall(r"[\d.]+", str(dimensions))
        if len(match) >= 3:
            l, w, h = (float(match[i]) for i in range(3))
            return l * w * h
        return None
