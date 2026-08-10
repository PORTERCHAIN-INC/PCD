"""Core pricing calculation engine."""

from __future__ import annotations

from porterchain_pricing.contract import ContractService
from porterchain_pricing.distance import estimate_duration_minutes, total_route_meters
from porterchain_pricing.gta_rate import (
    GtaRateConfig,
    calculate_gta_delivery_rate,
    default_gta_rate_config,
    detect_location_flags,
    normalize_vehicle_type,
)
from porterchain_pricing.promotion import PromotionService
from porterchain_pricing.rate_card import default_rate_card
from porterchain_pricing.tax import TaxService
from porterchain_pricing.types import PriceBreakdown, PricingContext, PricingRequest
from porterchain_pricing.zone import ZoneService


class PricingEngine:
    """Retail + merchant price calculation — Fleetbase never involved.

    Retail (and merchant without contract) uses the GTA delivery rate matrix:
    base covers N km, then extra km + extra pickup/drop fees + flat location surcharges.
    Rates come from admin Settings → Pricing (`ctx.gta_rate`) or built-in defaults.
    """

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
        distance_km = max((distance_meters or 0) / 1000.0, 0.0)

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
        zone_code, _zone_mult = zone_svc.zone_multiplier(request.pickup, request.dropoff)
        lane_code = zone_svc.resolve_lane(request.pickup, request.dropoff, ctx)
        breakdown.zone_code = zone_code

        if request.channel == "merchant" and (ctx.contract or ctx.merchant_pricing_config or ctx.tariffs):
            self.contracts.apply_contract(
                request, ctx, breakdown, distance_km=max(distance_km, 1.0), zone_code=zone_code, lane_code=lane_code
            )

        if breakdown.base_cents == 0:
            self._apply_gta_rate(
                request,
                breakdown,
                distance_km=distance_km,
                gta_cfg=ctx.gta_rate or default_gta_rate_config(),
            )

        if request.channel == "merchant" and request.requires_liftgate and card.liftgate_cents:
            breakdown.add_item("liftgate", "Liftgate service", card.liftgate_cents)

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

    def _apply_gta_rate(
        self,
        request: PricingRequest,
        breakdown: PriceBreakdown,
        *,
        distance_km: float,
        gta_cfg: GtaRateConfig,
    ) -> None:
        total_pickups = request.total_pickups if request.total_pickups is not None else 1
        total_drops = (
            request.total_drops
            if request.total_drops is not None
            else 1 + len(request.additional_stops or [])
        )

        if request.is_downtown is None or request.is_upper_zone is None:
            detected_downtown, detected_upper = detect_location_flags(
                request.pickup, request.dropoff, request.additional_stops
            )
            is_downtown = detected_downtown if request.is_downtown is None else request.is_downtown
            is_upper_zone = detected_upper if request.is_upper_zone is None else request.is_upper_zone
        else:
            is_downtown = request.is_downtown
            is_upper_zone = request.is_upper_zone

        try:
            matrix_vehicle = normalize_vehicle_type(request.vehicle_class, known=gta_cfg.vehicles)
        except ValueError:
            matrix_vehicle = "cargo_van"

        result = calculate_gta_delivery_rate(
            vehicle_type=matrix_vehicle,
            total_km=distance_km,
            total_pickups=total_pickups,
            total_drops=total_drops,
            is_downtown=bool(is_downtown),
            is_upper_zone=bool(is_upper_zone),
            config=gta_cfg,
        )

        breakdown.base_cents = result.distance_cost_cents
        breakdown.distance_cents = result.distance_cost_cents
        km_label = f"{gta_cfg.base_km_limit:g}"
        breakdown.add_item(
            "base",
            f"{result.vehicle_type.replace('_', ' ').title()} · up to {km_label} km base",
            result.distance_cost_cents,
        )

        if result.stop_fees_cents:
            extra_p = max(0, result.total_pickups - 1)
            extra_d = max(0, result.total_drops - 1)
            parts = []
            if extra_p:
                parts.append(f"{extra_p} extra pickup(s)")
            if extra_d:
                parts.append(f"{extra_d} extra drop(s)")
            breakdown.add_item("stop_fees", "Multi-stop fees (" + ", ".join(parts) + ")", result.stop_fees_cents)

        if result.downtown_fee_cents:
            breakdown.add_item("downtown", "Downtown Toronto surcharge", result.downtown_fee_cents)
        if result.upper_zone_fee_cents:
            breakdown.add_item("upper_zone", "Markham / North York surcharge", result.upper_zone_fee_cents)

        breakdown.metadata["pricing_model"] = "gta_delivery_rate"
        breakdown.metadata["gta_vehicle_type"] = result.vehicle_type
        breakdown.metadata["total_km"] = result.total_km
        breakdown.metadata["total_pickups"] = result.total_pickups
        breakdown.metadata["total_drops"] = result.total_drops
        breakdown.metadata["is_downtown"] = result.is_downtown
        breakdown.metadata["is_upper_zone"] = result.is_upper_zone
        breakdown.metadata["gta_total_cad"] = result.total_cad
        breakdown.metadata["base_km_limit"] = gta_cfg.base_km_limit
