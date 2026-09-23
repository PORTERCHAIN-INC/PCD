"""Core pricing calculation engine."""

from __future__ import annotations

from porterchain_pricing.components.distance import DistanceRateService
from porterchain_pricing.components.fsa import FsaRateService
from porterchain_pricing.components.location import LocationSurchargeService
from porterchain_pricing.components.size_weight import (
    DEFAULT_VOLUME_THRESHOLD_CM3,
    SizeWeightService,
    config_from_rate_card as size_weight_config_from_rate_card,
)
from porterchain_pricing.components.stops import StopFeeService
from porterchain_pricing.contract import ContractService
from porterchain_pricing.distance import estimate_duration_minutes, total_route_meters
from porterchain_pricing.gta_rate import (
    GtaRateConfig,
    default_gta_rate_config,
    normalize_vehicle_type,
)
from porterchain_pricing.policy import MODEL_DISTANCE, MODEL_FSA, MerchantPricingPolicy
from porterchain_pricing.promotion import PromotionService
from porterchain_pricing.rate_card import default_rate_card
from porterchain_pricing.tax import TaxService
from porterchain_pricing.types import PriceBreakdown, PricingContext, PricingRequest, SizeWeightConfig
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
        # Independently callable components — the same instances a caller can
        # use directly, so a component quote always matches the full quote.
        self.distance = DistanceRateService()
        self.stops = StopFeeService()
        self.location = LocationSurchargeService()
        self.size_weight = SizeWeightService()
        self.fsa = FsaRateService()

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
        breakdown.metadata["distance_km"] = round(distance_km, 3)
        breakdown.metadata["estimated_duration_minutes"] = duration
        if request.routing_source:
            breakdown.metadata["routing_source"] = request.routing_source

        from porterchain_pricing.components.fsa import fsa_from_point
        from porterchain_pricing.gta150_fsa import is_gta150_fsa

        origin_fsa = fsa_from_point(request.pickup) if request.pickup else ""
        dest_fsa = fsa_from_point(request.dropoff) if request.dropoff else ""
        breakdown.metadata["origin_fsa"] = origin_fsa or None
        breakdown.metadata["dest_fsa"] = dest_fsa or None
        breakdown.metadata["origin_in_tile"] = is_gta150_fsa(origin_fsa) if origin_fsa else None
        breakdown.metadata["dest_in_tile"] = is_gta150_fsa(dest_fsa) if dest_fsa else None
        breakdown.metadata["in_tile"] = bool(
            (not origin_fsa or is_gta150_fsa(origin_fsa))
            and (not dest_fsa or is_gta150_fsa(dest_fsa))
        )

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

        gta_cfg = ctx.gta_rate or default_gta_rate_config()

        policy = ctx.merchant_policy or MerchantPricingPolicy()
        breakdown.metadata["pricing_model_requested"] = policy.pricing_model

        # Base-price precedence, in order. The first one that produces a base
        # wins and the rest are skipped, so exactly one model sets the price:
        #   1. merchant-scoped tariff / MerchantContract rules
        #   2. FSA flat rate (merchant-scoped rows beat platform-wide rows)
        #   3. GTA distance matrix
        #
        # Global catalog tariffs must not enter this path — they used to set
        # base_cents and skip FSA / GTA for every merchant quote.
        if self.contracts.should_apply(request, ctx):
            self.contracts.apply_contract(
                request, ctx, breakdown, distance_km=max(distance_km, 1.0), zone_code=zone_code, lane_code=lane_code
            )

        # Retail is the published GTA card only — injected platform FSA rows
        # must not price a website quote.
        if (
            request.channel != "retail"
            and breakdown.base_cents == 0
            and ctx.fsa_rates
            and policy.pricing_model != MODEL_DISTANCE
        ):
            self._apply_fsa_rate(request, ctx, breakdown, gta_cfg=gta_cfg)

        if breakdown.base_cents == 0:
            if policy.pricing_model == MODEL_FSA:
                breakdown.metadata["fsa_fallback"] = True
            self._apply_gta_rate(
                request,
                breakdown,
                distance_km=distance_km,
                gta_cfg=gta_cfg,
                policy=policy,
            )

        self._apply_size_weight(request, ctx, breakdown)

        if request.channel == "merchant" and request.requires_liftgate and card.liftgate_cents:
            breakdown.add_item("liftgate", "Liftgate service", card.liftgate_cents)

        wait_rate = int(card.wait_cents_per_minute or 0)
        wait_minutes = float(request.wait_minutes or 0)
        if wait_rate > 0 and wait_minutes > 0:
            wait_cents = int(round(wait_minutes * wait_rate))
            breakdown.add_item("wait", f"Wait time ({wait_minutes:g} min)", wait_cents)
            breakdown.metadata["wait_minutes"] = wait_minutes

        # Customer distance fare has no fuel line. Merchant fuel is a percent of
        # the pre-tax charges, same truncation as HST.
        if request.channel != "retail":
            fuel_percent = float(ctx.fuel.surcharge_percent or 0)
            if fuel_percent > 0:
                fuel_base = sum(i.amount_cents for i in breakdown.items)
                fuel_cents = int(fuel_base * (fuel_percent / 100.0))
                breakdown.fuel_cents = fuel_cents
                breakdown.add_item("fuel", f"Fuel surcharge ({fuel_percent:g}%)", fuel_cents)

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

    def _stop_counts(self, request: PricingRequest) -> tuple[int, int]:
        pickups = request.total_pickups if request.total_pickups is not None else 1
        drops = (
            request.total_drops
            if request.total_drops is not None
            else 1 + len(request.additional_stops or [])
        )
        return pickups, drops

    def _matrix_vehicle(self, request: PricingRequest, gta_cfg: GtaRateConfig) -> str:
        try:
            return normalize_vehicle_type(request.vehicle_class, known=gta_cfg.vehicles)
        except ValueError:
            if request.channel == "retail":
                raise
            return "cargo_van"

    def _location_quote(
        self,
        request: PricingRequest,
        policy: MerchantPricingPolicy,
        *,
        gta_cfg: GtaRateConfig,
    ):
        """
        Location surcharges, with the merchant's own opt-outs applied.

        Turning a surcharge off forces its flag false rather than filtering the
        line item afterwards, so the detected-location metadata still reflects
        what the merchant is not being charged for.
        """
        return self.location.quote(
            pickup=request.pickup,
            dropoff=request.dropoff,
            additional_stops=request.additional_stops,
            is_downtown=False if not policy.charge_downtown else request.is_downtown,
            is_upper_zone=False if not policy.charge_upper_zone else request.is_upper_zone,
            config=gta_cfg,
        )

    def _apply_fsa_rate(
        self,
        request: PricingRequest,
        ctx: PricingContext,
        breakdown: PriceBreakdown,
        *,
        gta_cfg: GtaRateConfig,
    ) -> bool:
        """
        Price from the FSA table when a rate covers this destination.

        The flat rate *replaces* the distance charge rather than stacking on it.
        Extra stops are still billed because they are extra work, not extra
        geography; location surcharges are billed only when the matching row
        says its price does not already include them.
        """
        quote = self.fsa.quote(
            ctx.fsa_rates,
            pickup=request.pickup,
            dropoff=request.dropoff,
            merchant_id=request.merchant_id,
            vehicle_class=request.vehicle_class,
        )
        breakdown.metadata["fsa"] = quote.metadata
        if not quote.applies:
            return False

        breakdown.base_cents = quote.total_cents
        breakdown.distance_cents = 0
        for item in quote.items:
            breakdown.add_item(item.code, item.label, item.amount_cents)

        pickups, drops = self._stop_counts(request)
        matrix_vehicle = self._matrix_vehicle(request, gta_cfg)
        stops_q = self.stops.quote(
            vehicle_type=matrix_vehicle, total_pickups=pickups, total_drops=drops, config=gta_cfg
        )
        for item in stops_q.items:
            breakdown.add_item(item.code, item.label, item.amount_cents)

        if not quote.metadata.get("includes_location_fees", True):
            location_q = self._location_quote(
                request, ctx.merchant_policy or MerchantPricingPolicy(), gta_cfg=gta_cfg
            )
            for item in location_q.items:
                breakdown.add_item(item.code, item.label, item.amount_cents)
            breakdown.metadata.update(location_q.metadata)

        breakdown.metadata["pricing_model"] = "fsa_flat_rate"
        breakdown.metadata["total_pickups"] = pickups
        breakdown.metadata["total_drops"] = drops
        return True

    def _apply_size_weight(
        self,
        request: PricingRequest,
        ctx: PricingContext,
        breakdown: PriceBreakdown,
    ) -> None:
        """
        Size and weight charges.

        A merchant with its own size table is billed from that table alone; the
        rate-card thresholds are the platform fallback for everyone else. The
        two are deliberately not combined — a merchant who negotiated banded
        pricing should not also collect a per-kg overweight fee.
        """
        policy = ctx.merchant_policy or MerchantPricingPolicy()
        gta_cfg = ctx.gta_rate
        if request.channel != "retail" and policy.size_tiers:
            quote = self.size_weight.quote_tiers(
                policy.size_tiers, weight_kg=request.weight_kg, dimensions=request.dimensions
            )
        elif request.channel == "retail" and gta_cfg is not None and gta_cfg.weight_threshold_kg is not None:
            quote = self.size_weight.quote(
                weight_kg=request.weight_kg,
                dimensions=request.dimensions,
                declared_value_cents=request.declared_value_cents,
                volume_cm3=request.volume_cm3,
                config=SizeWeightConfig(
                    weight_threshold_kg=float(gta_cfg.weight_threshold_kg),
                    weight_cents_per_kg=int(gta_cfg.weight_cents_per_kg or 0),
                    volume_threshold_cm3=float(
                        gta_cfg.volume_threshold_cm3
                        if gta_cfg.volume_threshold_cm3 is not None
                        else DEFAULT_VOLUME_THRESHOLD_CM3
                    ),
                    cents_per_10k_cm3=int(gta_cfg.cents_per_10k_cm3 or 0),
                    declared_value_threshold_cents=int(gta_cfg.declared_value_threshold_cents or 0),
                    declared_value_rate=float(gta_cfg.declared_value_rate or 0),
                ),
            )
        else:
            quote = self.size_weight.quote(
                weight_kg=request.weight_kg,
                dimensions=request.dimensions,
                declared_value_cents=request.declared_value_cents,
                volume_cm3=request.volume_cm3,
                config=size_weight_config_from_rate_card(ctx.rate_card or default_rate_card()),
            )
        if not quote.applies:
            return
        for item in quote.items:
            breakdown.add_item(item.code, item.label, item.amount_cents)
        breakdown.weight_cents = quote.metadata.get("weight_cents", 0)
        breakdown.metadata["size_weight"] = quote.metadata

    def _apply_gta_rate(
        self,
        request: PricingRequest,
        breakdown: PriceBreakdown,
        *,
        distance_km: float,
        gta_cfg: GtaRateConfig,
        policy: MerchantPricingPolicy | None = None,
    ) -> None:
        policy = policy or MerchantPricingPolicy()
        total_pickups, total_drops = self._stop_counts(request)
        is_downtown, is_upper_zone = self.location.resolve_flags(
            pickup=request.pickup,
            dropoff=request.dropoff,
            additional_stops=request.additional_stops,
            is_downtown=request.is_downtown,
            is_upper_zone=request.is_upper_zone,
        )
        matrix_vehicle = self._matrix_vehicle(request, gta_cfg)

        distance_q = self.distance.quote(
            vehicle_type=matrix_vehicle, total_km=distance_km, config=gta_cfg
        )
        stops_q = self.stops.quote(
            vehicle_type=matrix_vehicle,
            total_pickups=total_pickups,
            total_drops=total_drops,
            config=gta_cfg,
        )
        location_q = self.location.quote(
            is_downtown=is_downtown and policy.charge_downtown,
            is_upper_zone=is_upper_zone and policy.charge_upper_zone,
            config=gta_cfg,
        )

        distance_cents = distance_q.metadata["distance_cost_cents"]
        breakdown.base_cents = distance_cents
        breakdown.distance_cents = distance_cents
        for component in (distance_q, stops_q, location_q):
            for item in component.items:
                breakdown.add_item(item.code, item.label, item.amount_cents)

        breakdown.metadata["pricing_model"] = "gta_delivery_rate"
        breakdown.metadata["gta_vehicle_type"] = matrix_vehicle
        breakdown.metadata["total_km"] = distance_q.metadata["total_km"]
        breakdown.metadata["total_pickups"] = total_pickups
        breakdown.metadata["total_drops"] = total_drops
        # What the trip is, versus what the merchant is billed for — a waived
        # surcharge should be visible rather than looking like a detection miss.
        breakdown.metadata["is_downtown"] = is_downtown
        breakdown.metadata["is_upper_zone"] = is_upper_zone
        if is_downtown and not policy.charge_downtown:
            breakdown.metadata["downtown_waived"] = True
        if is_upper_zone and not policy.charge_upper_zone:
            breakdown.metadata["upper_zone_waived"] = True
        breakdown.metadata["gta_total_cad"] = round(
            (distance_cents + stops_q.total_cents + location_q.total_cents) / 100.0, 2
        )
        breakdown.metadata["base_km_limit"] = gta_cfg.base_km_limit
