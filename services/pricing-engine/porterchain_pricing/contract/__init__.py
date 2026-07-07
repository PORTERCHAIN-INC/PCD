"""Merchant contract pricing — zones, lanes, flat rates, volume discounts."""

from __future__ import annotations

from datetime import datetime

from porterchain_pricing.catalog import VEHICLE_BASE_CENTS_PER_KM, VEHICLE_MINIMUM_CENTS
from porterchain_pricing.types import (
    ContractRecord,
    PriceBreakdown,
    PricingContext,
    PricingRequest,
    TariffRecord,
)


class ContractService:
    def select_tariff(
        self,
        ctx: PricingContext,
        request: PricingRequest,
        *,
        zone_code: str | None,
        lane_code: str | None,
    ) -> TariffRecord | None:
        candidates = [t for t in ctx.tariffs if t.merchant_id in (None, request.merchant_id)]
        if request.merchant_id:
            merchant_tariffs = [t for t in candidates if t.merchant_id == request.merchant_id]
            if merchant_tariffs:
                candidates = merchant_tariffs

        for tariff_type, match_value in (
            ("lane", lane_code),
            ("zone", zone_code),
            ("vehicle", request.vehicle_class),
            ("flat", request.service_type),
            ("retail", "retail"),
            ("merchant", "merchant"),
        ):
            if not match_value:
                continue
            for tariff in candidates:
                if tariff.tariff_type != tariff_type:
                    continue
                if tariff_type in ("zone", "vehicle", "lane") and tariff.zone and tariff.zone != match_value:
                    if tariff_type == "zone" and tariff.zone != match_value:
                        continue
                if tariff_type == "vehicle" and tariff.vehicle_class and tariff.vehicle_class != request.vehicle_class:
                    continue
                if tariff_type == "lane" and tariff.config.get("lane") != match_value:
                    continue
                return tariff
        return None

    def apply_contract(
        self,
        request: PricingRequest,
        ctx: PricingContext,
        breakdown: PriceBreakdown,
        *,
        distance_km: float,
        zone_code: str | None,
        lane_code: str | None,
    ) -> None:
        contract = ctx.contract
        config = ctx.merchant_pricing_config

        tariff = self.select_tariff(ctx, request, zone_code=zone_code, lane_code=lane_code)
        if tariff:
            breakdown.contract_id = tariff.id
            per_km = tariff.per_km_cents or VEHICLE_BASE_CENTS_PER_KM.get(request.vehicle_class, 145)
            base = tariff.base_cents or VEHICLE_MINIMUM_CENTS.get(request.vehicle_class, 3499)
            distance_charge = int(distance_km * per_km)
            raw_base = max(distance_charge, base)
            breakdown.base_cents = raw_base
            breakdown.distance_cents = distance_charge
            breakdown.add_item("base", tariff.name, raw_base)
            if tariff.fuel_surcharge_percent:
                ctx.fuel.surcharge_percent = tariff.fuel_surcharge_percent

        if contract:
            breakdown.contract_id = contract.id
            rules = contract.rules

            flat_rate = rules.get("flat_rates", {}).get(request.service_type)
            if isinstance(flat_rate, int):
                breakdown.base_cents = flat_rate
                breakdown.add_item("flat_rate", f"Flat rate ({request.service_type})", flat_rate)

            lane_rates = rules.get("lane_pricing", {})
            if lane_code and lane_code in lane_rates:
                lane_cents = int(lane_rates[lane_code])
                breakdown.base_cents = lane_cents
                breakdown.add_item("lane", f"Lane {lane_code}", lane_cents)

            zone_rates = rules.get("zone_pricing", {})
            if zone_code and zone_code in zone_rates:
                zone_cents = int(zone_rates[zone_code])
                breakdown.add_item("zone", f"Zone {zone_code}", zone_cents)

            vehicle_rates = rules.get("vehicle_pricing", {})
            if request.vehicle_class in vehicle_rates:
                vehicle_extra = int(vehicle_rates[request.vehicle_class])
                breakdown.vehicle_cents += vehicle_extra
                breakdown.add_item("contract_vehicle", f"Contract vehicle ({request.vehicle_class})", vehicle_extra)

        if config:
            custom_rules = config.get("custom_rules", [])
            for rule in custom_rules:
                if not isinstance(rule, dict):
                    continue
                if rule.get("vehicle_class") and rule["vehicle_class"] != request.vehicle_class:
                    continue
                if rule.get("service_type") and rule["service_type"] != request.service_type:
                    continue
                amount = int(rule.get("amount_cents", 0))
                if amount:
                    breakdown.add_item("custom_rule", rule.get("label", "Custom rule"), amount)

            volume_discounts = config.get("volume_discounts", [])
            for tier in sorted(volume_discounts, key=lambda t: t.get("min_units", 0), reverse=True):
                min_units = int(tier.get("min_units", 0))
                if request.volume_units >= min_units:
                    pct = float(tier.get("discount_percent", 0))
                    if pct:
                        discount = int(breakdown.subtotal_cents * pct / 100) if breakdown.subtotal_cents else 0
                        if discount:
                            breakdown.discount_cents += discount
                            breakdown.add_item("volume_discount", f"Volume discount ({pct}%)", -discount)
                    break

        self._apply_time_multipliers(request, ctx, breakdown)

    def _apply_time_multipliers(self, request: PricingRequest, ctx: PricingContext, breakdown: PriceBreakdown) -> None:
        config = ctx.merchant_pricing_config
        contract_rules = ctx.contract.rules if ctx.contract else {}

        scheduled_at = request.scheduled_at or datetime.now()
        is_weekend = scheduled_at.weekday() >= 5
        is_holiday = scheduled_at.strftime("%m-%d") in set(config.get("holidays", contract_rules.get("holidays", [])))

        weekend_mult = float(config.get("weekend_multiplier", contract_rules.get("weekend_multiplier", 1.0)))
        holiday_mult = float(config.get("holiday_multiplier", contract_rules.get("holiday_multiplier", 1.0)))

        if is_weekend and weekend_mult > 1.0:
            surcharge = int((breakdown.base_cents + breakdown.distance_cents) * (weekend_mult - 1.0))
            if surcharge:
                breakdown.add_item("weekend", "Weekend pricing", surcharge)

        if is_holiday and holiday_mult > 1.0:
            surcharge = int((breakdown.base_cents + breakdown.distance_cents) * (holiday_mult - 1.0))
            if surcharge:
                breakdown.add_item("holiday", "Holiday pricing", surcharge)
