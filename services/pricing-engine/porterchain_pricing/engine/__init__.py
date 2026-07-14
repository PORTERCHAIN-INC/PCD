"""Core pricing calculation engine."""

from __future__ import annotations

from datetime import datetime

from porterchain_pricing.contract import ContractService
from porterchain_pricing.distance import estimate_duration_minutes, total_route_meters
from porterchain_pricing.promotion import PromotionService
from porterchain_pricing.rate_card import RateCard, default_rate_card
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
        card = ctx.rate_card or default_rate_card()
        breakdown = PriceBreakdown()

        distance_meters = request.distance_meters
        if distance_meters is None:
            distance_meters = total_route_meters(request.pickup, request.dropoff, request.additional_stops)
        distance_km = max((distance_meters or 5000) / 1000.0, 1.0)

        duration = request.estimated_duration_minutes or estimate_duration_minutes(distance_meters)
        breakdown.metadata["distance_meters"] = distance_meters
        breakdown.metadata["estimated_duration_minutes"] = duration
        if request.routing_source:
            breakdown.metadata["routing_source"] = request.routing_source
        breakdown.metadata["driver_share_pct"] = card.driver_share_pct
        breakdown.metadata["platform_share_pct"] = card.platform_share_pct
        breakdown.metadata["driver_payout_mode"] = card.driver_payout_mode
        breakdown.metadata["driver_flat_per_delivery_cents"] = card.driver_flat_per_delivery_cents
        breakdown.metadata["driver_minimum_payout_cents"] = card.driver_minimum_payout_cents
        if card.driver_payout_mode == "flat":
            breakdown.metadata["driver_payout_cents_preview"] = card.compute_driver_payout_cents()

        zone_svc = self.zones.with_context(ctx)
        zone_code, zone_mult = zone_svc.zone_multiplier(request.pickup, request.dropoff)
        lane_code = zone_svc.resolve_lane(request.pickup, request.dropoff, ctx)
        breakdown.zone_code = zone_code

        vehicle = request.vehicle_class
        vehicle_rate = card.vehicle(vehicle)
        if vehicle not in card.vehicles and card.vehicle(_to_camel(vehicle)).per_km_cents:
            vehicle = _to_camel(vehicle)
            vehicle_rate = card.vehicle(vehicle)

        if request.channel == "merchant" and (ctx.contract or ctx.merchant_pricing_config or ctx.tariffs):
            self.contracts.apply_contract(
                request, ctx, breakdown, distance_km=distance_km, zone_code=zone_code, lane_code=lane_code
            )

        if breakdown.base_cents == 0:
            self._apply_retail_base(
                request, breakdown, card=card, vehicle=vehicle, distance_km=distance_km, zone_mult=zone_mult
            )

        if card.base_fee_cents:
            breakdown.add_item("base_fee", "Base fee", card.base_fee_cents)

        self._apply_vehicle_charge(breakdown, vehicle, vehicle_rate.surcharge_cents)
        self._apply_per_minute(breakdown, card, duration)
        self._apply_wait_time(request, breakdown, card)
        self._apply_package_and_service(request, breakdown, card)
        self._apply_weight_and_dimensions(request, breakdown, card)
        self._apply_declared_value(request, breakdown, card)
        self._apply_schedule_and_rush(request, breakdown, card)
        self._apply_extra_stops(request, breakdown, card)
        self._apply_liftgate(request, breakdown, card)
        self._apply_time_multipliers(request, breakdown, card)
        self._apply_fuel_surcharge(ctx, breakdown)

        breakdown.subtotal_cents = sum(i.amount_cents for i in breakdown.items)
        self._apply_minimum(request, ctx, breakdown, card, vehicle)

        breakdown.subtotal_cents = sum(i.amount_cents for i in breakdown.items)
        self.promotions.apply(request, ctx, breakdown)
        breakdown.subtotal_cents = sum(i.amount_cents for i in breakdown.items)

        tax_svc = self.tax.with_context(ctx)
        breakdown.tax_cents = tax_svc.calculate(request, breakdown)
        breakdown.finalize()
        if card.driver_payout_mode == "percent":
            breakdown.metadata["driver_payout_cents_preview"] = card.compute_driver_payout_cents(
                order_amount_cents=breakdown.final_cents
            )
        return breakdown

    def _apply_retail_base(
        self,
        request: PricingRequest,
        breakdown: PriceBreakdown,
        *,
        card: RateCard,
        vehicle: str,
        distance_km: float,
        zone_mult: float,
    ) -> None:
        rate = card.vehicle(vehicle)
        distance_charge = int(distance_km * rate.per_km_cents * zone_mult)
        minimum = int(rate.minimum_cents * zone_mult)
        base = max(distance_charge, minimum)
        breakdown.base_cents = base
        breakdown.distance_cents = distance_charge
        breakdown.add_item("base", f"{vehicle} delivery", base)

    def _apply_vehicle_charge(self, breakdown: PriceBreakdown, vehicle: str, surcharge: int) -> None:
        if surcharge:
            breakdown.vehicle_cents = surcharge
            breakdown.add_item("vehicle", f"Vehicle ({vehicle})", surcharge)

    def _apply_per_minute(self, breakdown: PriceBreakdown, card: RateCard, duration: float | int | None) -> None:
        if not card.per_minute_cents or not duration:
            return
        amount = int(float(duration) * card.per_minute_cents)
        breakdown.add_item("per_minute", f"Time ({duration} min)", amount)

    def _apply_wait_time(self, request: PricingRequest, breakdown: PriceBreakdown, card: RateCard) -> None:
        if not card.wait_cents_per_minute or request.wait_minutes <= 0:
            return
        amount = int(request.wait_minutes * card.wait_cents_per_minute)
        breakdown.add_item("wait", f"Wait time ({request.wait_minutes:g} min)", amount)

    def _apply_package_and_service(
        self, request: PricingRequest, breakdown: PriceBreakdown, card: RateCard
    ) -> None:
        pkg = card.package_surcharges.get(request.package_type, 0)
        if pkg:
            breakdown.add_item("package", f"Package ({request.package_type})", pkg)

        svc = card.service_surcharges.get(request.service_type, 0)
        if svc:
            breakdown.add_item("service", f"Service ({request.service_type})", svc)

    def _apply_weight_and_dimensions(
        self, request: PricingRequest, breakdown: PriceBreakdown, card: RateCard
    ) -> None:
        if request.weight_kg and request.weight_kg > card.weight_threshold_kg and card.weight_cents_per_kg:
            extra = int((request.weight_kg - card.weight_threshold_kg) * card.weight_cents_per_kg)
            breakdown.weight_cents = extra
            breakdown.add_item("weight", "Weight surcharge", extra)

    def _apply_declared_value(
        self, request: PricingRequest, breakdown: PriceBreakdown, card: RateCard
    ) -> None:
        if (
            request.declared_value_cents
            and request.declared_value_cents > card.declared_value_threshold_cents
            and card.declared_value_rate
        ):
            insurance = int(request.declared_value_cents * card.declared_value_rate)
            breakdown.add_item("declared_value", "Declared value coverage", insurance)

    def _apply_schedule_and_rush(
        self, request: PricingRequest, breakdown: PriceBreakdown, card: RateCard
    ) -> None:
        if request.is_rush or request.schedule_mode == "now":
            if request.service_type != "express":
                breakdown.add_item("rush", "Rush delivery", card.rush_surcharge_cents)
        elif request.schedule_mode == "later" or request.service_type == "scheduled":
            breakdown.add_item("scheduled", "Scheduled delivery", card.scheduled_surcharge_cents)

    def _apply_extra_stops(
        self, request: PricingRequest, breakdown: PriceBreakdown, card: RateCard
    ) -> None:
        count = len(request.additional_stops)
        if count and card.extra_stop_cents:
            amount = count * card.extra_stop_cents
            breakdown.add_item("additional_stops", f"Extra stops ({count})", amount)

    def _apply_liftgate(self, request: PricingRequest, breakdown: PriceBreakdown, card: RateCard) -> None:
        if request.requires_liftgate and card.liftgate_cents:
            breakdown.add_item("liftgate", "Liftgate service", card.liftgate_cents)

    def _apply_time_multipliers(
        self, request: PricingRequest, breakdown: PriceBreakdown, card: RateCard
    ) -> None:
        scheduled_at = request.scheduled_at or datetime.now()
        is_weekend = scheduled_at.weekday() >= 5
        is_holiday = scheduled_at.strftime("%m-%d") in set(card.holidays)
        hour = scheduled_at.hour
        if card.night_start_hour >= card.night_end_hour:
            is_night = hour >= card.night_start_hour or hour < card.night_end_hour
        else:
            is_night = card.night_start_hour <= hour < card.night_end_hour

        chargeable = breakdown.base_cents + breakdown.distance_cents
        if is_weekend and card.weekend_multiplier > 1.0:
            surcharge = int(chargeable * (card.weekend_multiplier - 1.0))
            if surcharge:
                breakdown.add_item("weekend", "Weekend pricing", surcharge)
        if is_holiday and card.holiday_multiplier > 1.0:
            surcharge = int(chargeable * (card.holiday_multiplier - 1.0))
            if surcharge:
                breakdown.add_item("holiday", "Holiday pricing", surcharge)
        if is_night and card.night_multiplier > 1.0:
            surcharge = int(chargeable * (card.night_multiplier - 1.0))
            if surcharge:
                breakdown.add_item("night", "Night / after-hours", surcharge)

    def _apply_fuel_surcharge(self, ctx: PricingContext, breakdown: PriceBreakdown) -> None:
        chargeable = breakdown.base_cents + breakdown.distance_cents + breakdown.vehicle_cents + breakdown.weight_cents
        chargeable += sum(
            i.amount_cents
            for i in breakdown.items
            if i.code
            in (
                "package",
                "service",
                "rush",
                "scheduled",
                "additional_stops",
                "liftgate",
                "base_fee",
                "per_minute",
                "wait",
                "weekend",
                "holiday",
                "night",
            )
        )
        pct = ctx.fuel.surcharge_percent
        if pct and chargeable > 0:
            fuel = int(chargeable * pct / 100)
            breakdown.fuel_cents = fuel
            breakdown.add_item("fuel", f"Fuel surcharge ({pct}%)", fuel)

    def _apply_minimum(
        self,
        request: PricingRequest,
        ctx: PricingContext,
        breakdown: PriceBreakdown,
        card: RateCard,
        vehicle: str,
    ) -> None:
        minimum = card.vehicle(vehicle).minimum_cents
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


def _to_camel(value: str) -> str:
    parts = value.replace("-", "_").split("_")
    if len(parts) == 1:
        return value
    return parts[0] + "".join(p.title() for p in parts[1:])
