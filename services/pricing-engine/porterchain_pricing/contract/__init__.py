"""Merchant contract pricing — zones, lanes, flat rates, volume discounts."""

from __future__ import annotations

from porterchain_pricing.types import (
    PriceBreakdown,
    PricingContext,
    PricingRequest,
    TariffRecord,
)


def _vehicle_matches(tariff_vehicle: str | None, request_vehicle: str) -> bool:
    """Loose vehicle match — seed rows use cargoVan vs cargo_van interchangeably."""
    if not tariff_vehicle:
        return True
    a = tariff_vehicle.replace("_", "").replace("-", "").lower()
    b = (request_vehicle or "").replace("_", "").replace("-", "").lower()
    return a == b


class ContractService:
    def should_apply(self, request: PricingRequest, ctx: PricingContext) -> bool:
        """
        True only when a negotiated commercial layer is actually in play.

        Global catalog tariffs (retail / unscoped merchant) must not force this
        path — that used to set base_cents and skip FSA / GTA for every merchant.
        """
        if request.channel != "merchant":
            return False
        if ctx.contract and ctx.contract.is_active:
            return True
        if request.merchant_id and any(
            t.merchant_id == request.merchant_id for t in (ctx.tariffs or [])
        ):
            return True
        cfg = ctx.merchant_pricing_config or {}
        if cfg.get("custom_rules") or cfg.get("volume_discounts"):
            return True
        return False

    def select_tariff(
        self,
        ctx: PricingContext,
        request: PricingRequest,
        *,
        zone_code: str | None,
        lane_code: str | None,
    ) -> TariffRecord | None:
        """
        Pick the most specific negotiated tariff for this quote.

        Lane / zone / vehicle / flat rows may be platform-wide or merchant-scoped.
        Channel catalog rows (`retail` / `merchant`) only match their own channel,
        and `merchant` rows require `merchant_id == request.merchant_id` so a seed
        or production catalog row cannot steal FSA / GTA bases.
        """
        channel = (request.channel or "").strip().lower()
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
        ):
            if not match_value:
                continue
            for tariff in candidates:
                if tariff.tariff_type != tariff_type:
                    continue
                if tariff_type == "zone" and tariff.zone and tariff.zone != match_value:
                    continue
                if tariff_type == "vehicle":
                    if tariff.zone and zone_code and tariff.zone != zone_code:
                        continue
                    if not _vehicle_matches(tariff.vehicle_class, request.vehicle_class):
                        continue
                if tariff_type == "lane" and tariff.config.get("lane") != match_value:
                    continue
                return tariff

        if channel == "merchant" and request.merchant_id:
            for tariff in candidates:
                if tariff.tariff_type != "merchant":
                    continue
                if tariff.merchant_id != request.merchant_id:
                    continue
                if not _vehicle_matches(tariff.vehicle_class, request.vehicle_class):
                    continue
                return tariff
        elif channel == "retail":
            for tariff in candidates:
                if tariff.tariff_type != "retail":
                    continue
                if tariff.merchant_id is not None:
                    continue
                if not _vehicle_matches(tariff.vehicle_class, request.vehicle_class):
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

        card = ctx.rate_card
        vehicle_rate = card.vehicle(request.vehicle_class) if card else None
        default_per_km = vehicle_rate.per_km_cents if vehicle_rate else 100
        default_min = vehicle_rate.minimum_cents if vehicle_rate else 100

        tariff = self.select_tariff(ctx, request, zone_code=zone_code, lane_code=lane_code)
        if tariff:
            breakdown.contract_id = tariff.id
            per_km = tariff.per_km_cents or default_per_km
            base = tariff.base_cents or default_min
            distance_charge = int(distance_km * per_km)
            raw_base = max(distance_charge, base)
            breakdown.base_cents = raw_base
            breakdown.distance_cents = distance_charge
            breakdown.add_item("base", tariff.name, raw_base)
            breakdown.metadata["pricing_model"] = "contract_tariff"
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
