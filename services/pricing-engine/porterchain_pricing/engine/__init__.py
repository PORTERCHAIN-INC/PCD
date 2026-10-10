"""Core pricing calculation engine."""

from __future__ import annotations

from porterchain_pricing.components.contract_route import ContractRouteService
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
from porterchain_pricing.contract_schedule import ContractSchedule, load_contract_schedule
from porterchain_pricing.distance import estimate_duration_minutes, total_route_meters
from porterchain_pricing.gta_rate import (
    GtaRateConfig,
    default_gta_rate_config,
    normalize_vehicle_type,
)
from porterchain_pricing.policy import (
    FSA_MISS_REFUSE,
    MODEL_FSA,
    MerchantPricingPolicy,
)
from porterchain_pricing.price_book import (
    BookParcel,
    dedicated_charge,
    effective_price_book,
    price_parcels,
    retail_charge,
)
from porterchain_pricing.promotion import PromotionService
from porterchain_pricing.rate_card import default_rate_card
from porterchain_pricing.tax import TaxService
from porterchain_pricing.types import PriceBreakdown, PricingContext, PricingRequest, SizeWeightConfig
from porterchain_pricing.zone import ZoneService


class PricingEngine:
    """Retail + merchant price calculation (PorterChain; no vendor dispatch).

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
        self.contract_route = ContractRouteService()

    def calculate(self, request: PricingRequest, ctx: PricingContext | None = None) -> PriceBreakdown:
        ctx = ctx or PricingContext()
        card = ctx.rate_card or default_rate_card()
        breakdown = PriceBreakdown()
        # Every quote carries the pricing-settings version it was priced with.
        breakdown.metadata["price_version"] = ctx.price_version

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
        zone_code, zone_mult = zone_svc.zone_multiplier(request.pickup, request.dropoff)
        lane_code = zone_svc.resolve_lane(request.pickup, request.dropoff, ctx)
        breakdown.zone_code = zone_code
        breakdown.metadata["zone_multiplier"] = zone_mult

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

        # A merchant on a checked-in contract schedule is priced per stop and
        # per parcel from that schedule — no FSA rows, distance stop fees, zone
        # multiplier, location surcharges or generic size tiers.
        schedule_terms = self._contract_schedule(request, policy, breakdown)
        route_priced = False
        if schedule_terms is not None and breakdown.base_cents == 0:
            if not self._apply_contract_route(request, schedule_terms, breakdown):
                breakdown.finalize()
                return breakdown
            route_priced = True

        # Price book: whole-vehicle (dedicated) and the one retail price are
        # fixed prices that replace the stop / distance base. OFF by default.
        book = self._price_book(request, ctx, breakdown)
        fixed_priced = False
        if not route_priced and breakdown.base_cents == 0 and book is not None:
            fixed_priced = self._apply_fixed_price(request, book, breakdown)
        book_parcels = bool(
            book is not None
            and not route_priced
            and not fixed_priced
            and request.channel == "merchant"
            and request.booking_mode != "vehicle"
            and book["merchant_parcels"]["enabled"]
        )

        # Retail is the published GTA card only — injected platform FSA rows
        # must not price a website quote.
        if (
            not route_priced
            and request.channel != "retail"
            and breakdown.base_cents == 0
            and ctx.fsa_rates
            and policy.pricing_model == MODEL_FSA
        ):
            self._apply_fsa_rate(request, ctx, breakdown, gta_cfg=gta_cfg)

        if breakdown.base_cents == 0 and book_parcels and policy.pricing_model == MODEL_FSA:
            # Price-book merchant with no FSA row: the default stop price per drop.
            self._apply_book_stop_price(request, book, breakdown)

        if breakdown.base_cents == 0:
            if policy.pricing_model == MODEL_FSA:
                if policy.schedule.fsa_miss == FSA_MISS_REFUSE:
                    breakdown.metadata["fsa_refused"] = True
                    breakdown.metadata["pricing_model"] = "fsa_refused"
                    # Fail closed — no size / pickup / fuel / tax on a refused FSA miss.
                    breakdown.finalize()
                    return breakdown
                breakdown.metadata["fsa_fallback"] = True
            self._apply_gta_rate(
                request,
                breakdown,
                distance_km=distance_km,
                gta_cfg=gta_cfg,
                policy=policy,
            )

        if not route_priced and not fixed_priced:
            # Compact banding can replace FSA base when schedule says so.
            if request.channel != "retail":
                self._apply_compact_banding(request, ctx, breakdown)

            # Negotiated contract prices encode their own zone / lane terms, and
            # an FSA flat rate is an all-in price for that destination.
            if not breakdown.contract_id and breakdown.metadata.get("pricing_model") not in (
                "fsa_flat_rate",
                "price_book_stop",
            ):
                self._apply_zone_multiplier(breakdown, zone_mult)

            if book_parcels and not breakdown.metadata.get("compact_banding"):
                # Quantity tiers + small rule + handling replace generic size tiers.
                if not self._apply_book_parcels(request, book, breakdown):
                    breakdown.finalize()
                    return breakdown
            else:
                book_parcels = False
                self._apply_size_weight(request, ctx, breakdown)

        if request.channel == "merchant" and request.requires_liftgate and card.liftgate_cents:
            breakdown.add_item("liftgate", "Liftgate service", card.liftgate_cents)

        self._apply_coverage(request, ctx, breakdown)

        wait_rate = int(card.wait_cents_per_minute or 0)
        wait_minutes = float(request.wait_minutes or 0)
        if wait_rate > 0 and wait_minutes > 0:
            wait_cents = int(round(wait_minutes * wait_rate))
            breakdown.add_item("wait", f"Wait time ({wait_minutes:g} min)", wait_cents)
            breakdown.metadata["wait_minutes"] = wait_minutes

        if request.channel == "merchant":
            if not route_priced and not fixed_priced:
                self._apply_origin_pickup(request, policy, breakdown)
                self._apply_route_minimum(request, ctx, policy, breakdown)
                if book_parcels:
                    self._apply_book_minimum(request, book, breakdown)
            self.contracts.apply_volume_discount(request, ctx, breakdown)

        # Customer distance fare has no fuel line. Merchant fuel is a percent of
        # the pre-tax charges, same truncation as HST. Schedule override wins.
        if request.channel != "retail":
            if policy.schedule.fuel_surcharge_percent is not None:
                fuel_percent = float(policy.schedule.fuel_surcharge_percent)
            else:
                fuel_percent = float(ctx.fuel.surcharge_percent or 0)
            breakdown.metadata["fuel_surcharge_percent"] = fuel_percent
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

    # ------------------------------------------------------------ price book

    def _price_book(
        self, request: PricingRequest, ctx: PricingContext, breakdown: PriceBreakdown
    ) -> dict | None:
        """Effective book (global + merchant overrides); None if it is invalid."""
        merchant_cfg = ctx.merchant_pricing_config if request.channel == "merchant" else None
        try:
            return effective_price_book(ctx.price_book, merchant_cfg)
        except ValueError as exc:
            breakdown.metadata["price_book_invalid"] = str(exc)
            return None

    def _apply_fixed_price(self, request: PricingRequest, book: dict, breakdown: PriceBreakdown) -> bool:
        if request.booking_mode == "vehicle":
            vehicle = str(request.vehicle_class or "").lower()
            got = dedicated_charge(book, vehicle, request.dedicated_hours)
            if got is None:
                return False
            cents, units, unit = got
            label = "hour" if unit == "hour" else "half-day"
            breakdown.add_item("dedicated_vehicle", f"Dedicated {vehicle} ({units} × {label})", cents)
            breakdown.base_cents = cents
            breakdown.metadata["pricing_model"] = "dedicated"
            breakdown.metadata["dedicated_units"] = units
            breakdown.metadata["dedicated_unit"] = unit
            return True
        if request.channel == "retail":
            cents = retail_charge(book, request.parcel_count)
            if cents is None:
                return False
            breakdown.add_item("retail_fixed", "Delivery (fixed price)", cents)
            breakdown.base_cents = cents
            breakdown.metadata["pricing_model"] = "retail_fixed"
            return True
        return False

    def _apply_book_stop_price(self, request: PricingRequest, book: dict, breakdown: PriceBreakdown) -> None:
        drops = 1 + len(request.additional_stops or [])
        cents = int(book["stop_price_cents"]) * drops
        if cents <= 0:
            return
        breakdown.add_item("stop_price", f"Delivery ({drops} stop{'s' if drops != 1 else ''})", cents)
        breakdown.base_cents = cents
        breakdown.distance_cents = 0
        breakdown.metadata["pricing_model"] = "price_book_stop"

    def _apply_book_parcels(self, request: PricingRequest, book: dict, breakdown: PriceBreakdown) -> bool:
        """Parcel tier + handling lines. False = custom quote (route refused)."""
        from porterchain_pricing.components.size_weight import parse_dimensions_cm

        n_stops = 1 + len(request.additional_stops or [])
        parcels: list[BookParcel] = []
        if request.parcels:
            for spec in request.parcels:
                idx = spec.stop_index if 0 <= spec.stop_index < n_stops else 0
                parcels.append(
                    BookParcel(idx, spec.weight_kg, parse_dimensions_cm(spec.dimensions), spec.item_key)
                )
        else:
            total = max(int(request.parcel_count or 1), 1)
            each_kg = (float(request.weight_kg) / total) if request.weight_kg else None
            dims = parse_dimensions_cm(request.dimensions)
            parcels = [BookParcel(0, each_kg, dims) for _ in range(total)]
        multi = bool(book.get("multi_box_as_one_item"))
        charge = price_parcels(
            book,
            parcels,
            vehicle_class=request.vehicle_class,
            multi_box_as_one_item=multi,
            n_stops=n_stops,
        )
        if charge.custom_quote_reason:
            breakdown.items = []
            breakdown.base_cents = 0
            breakdown.metadata["fsa_refused"] = True
            breakdown.metadata["custom_quote"] = True
            breakdown.metadata["custom_quote_reason"] = charge.custom_quote_reason
            breakdown.metadata["pricing_model"] = "fsa_refused"
            return False
        units = sum(s.billable_units for s in charge.stops)
        if charge.parcel_cents:
            breakdown.add_item("parcel_tier", f"Parcels ({units} billable)", charge.parcel_cents)
        if charge.handling_cents:
            breakdown.add_item("handling", "Heavy / large item handling", charge.handling_cents)
        breakdown.metadata["price_book"] = {
            "billable_units": units,
            "small_boxes": sum(s.small_boxes for s in charge.stops),
            "tier_rates_cents": list(charge.tier_rates),
            "multi_box_as_one_item": multi,
            "handling": [c for s in charge.stops for c in s.handling_codes],
        }
        return True

    def _apply_book_minimum(self, request: PricingRequest, book: dict, breakdown: PriceBreakdown) -> None:
        if any(i.code == "route_minimum" for i in breakdown.items):
            return
        minimum = book["minimum"]
        drops = 1 + len(request.additional_stops or [])
        min_cents = minimum["cents"] * (drops if minimum["mode"] == "per_stop" else 1)
        top_up = min_cents - sum(i.amount_cents for i in breakdown.items)
        if top_up <= 0:
            return
        breakdown.add_item("route_minimum", "Route minimum", top_up)
        breakdown.metadata["route_minimum_cents"] = min_cents
        breakdown.metadata["route_minimum_top_up_cents"] = top_up

    def _contract_schedule(
        self,
        request: PricingRequest,
        policy: MerchantPricingPolicy,
        breakdown: PriceBreakdown,
    ) -> ContractSchedule | None:
        """The checked-in schedule named by an FSA-model merchant's policy, if any."""
        schedule_id = policy.schedule.contract_schedule
        if request.channel != "merchant" or policy.pricing_model != MODEL_FSA or not schedule_id:
            return None
        terms = load_contract_schedule(schedule_id)
        if terms is None:
            breakdown.metadata["contract_schedule_unknown"] = schedule_id
        return terms

    def _apply_contract_route(
        self,
        request: PricingRequest,
        schedule: ContractSchedule,
        breakdown: PriceBreakdown,
    ) -> bool:
        """Price the whole route from the schedule. False when it is a custom quote."""
        quote = self.contract_route.quote(request, schedule)
        if quote.metadata.get("refused"):
            breakdown.metadata.update(quote.metadata)
            breakdown.metadata["fsa_refused"] = True
            breakdown.metadata["custom_quote"] = True
            breakdown.metadata["pricing_model"] = "fsa_refused"
            return False
        for item in quote.items:
            breakdown.add_item(item.code, item.label, item.amount_cents)
        breakdown.base_cents = quote.total_cents
        breakdown.distance_cents = 0
        breakdown.metadata.update(quote.metadata)
        breakdown.metadata["pricing_model"] = "contract_route"
        return True

    def _apply_zone_multiplier(self, breakdown: PriceBreakdown, multiplier: float) -> None:
        """
        Scale the base charges by the admin-configured zone multiplier
        (`pricing_zones.multiplier`). Shown as its own line so the quote stays
        explainable; a multiplier of 1.0 (the default zones) adds nothing.

        Compact banding is an all-in territory rate — zone must not scale it
        (Ravi / pricing-audit-v2).
        """
        if breakdown.metadata.get("compact_banding"):
            return
        try:
            mult = float(multiplier)
        except (TypeError, ValueError):
            return
        if mult <= 0 or abs(mult - 1.0) < 1e-9:
            return
        charges = sum(i.amount_cents for i in breakdown.items if i.amount_cents > 0)
        if charges <= 0:
            return
        delta = int(round(charges * (mult - 1.0)))
        if delta == 0:
            return
        breakdown.add_item("zone_multiplier", f"Zone adjustment (×{mult:g})", delta)
        breakdown.base_cents = int(round(breakdown.base_cents * mult))
        breakdown.metadata["zone_multiplier_applied"] = mult
        breakdown.metadata["zone_multiplier_delta_cents"] = delta

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

        A merchant with its own table is priced from that table only — a
        platform-wide row must not fill a gap the merchant left unrated.
        """
        own = [r for r in ctx.fsa_rates if r.merchant_id and r.merchant_id == request.merchant_id]
        quote = self.fsa.quote(
            own or ctx.fsa_rates,
            pickup=request.pickup,
            dropoff=request.dropoff,
            merchant_id=request.merchant_id,
            vehicle_class=request.vehicle_class,
        )
        breakdown.metadata["fsa"] = quote.metadata
        if not quote.applies:
            return False

        rate_id = quote.metadata.get("rate_id")
        for row in ctx.fsa_rates:
            if row.id == rate_id:
                tier = (row.config or {}).get("tier")
                if tier:
                    breakdown.metadata["fsa_tier"] = str(tier)
                break

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
                policy.size_tiers,
                weight_kg=request.weight_kg,
                dimensions=request.dimensions,
                size_match=policy.schedule.size_match,
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

    def _apply_coverage(self, request: PricingRequest, ctx: PricingContext, breakdown: PriceBreakdown) -> None:
        """Declared-value cover: free tier always; opt-in upgrade adds one line."""
        from porterchain_pricing.coverage import charge_cents, coverage_label, normalize_coverage, recommend

        try:
            cfg = normalize_coverage(ctx.coverage)
        except ValueError:
            cfg = normalize_coverage(None)
        upgrade = request.coverage_upgrade
        if upgrade is None:
            mcfg = ctx.merchant_pricing_config or {}
            upgrade = bool(mcfg.get("coverage_upgrade_default", False))
        rec = recommend(request.declared_value_cents, request.item_category, cfg)
        cents = charge_cents(bool(upgrade), request.parcel_count, cfg)
        if cents:
            unit = " per parcel" if cfg["unit"] == "parcel" else ""
            breakdown.add_item("coverage_upgrade", coverage_label(True, cfg) + unit, cents)
        breakdown.metadata["coverage"] = {
            "tier": "upgrade" if upgrade else "included",
            "covered_up_to_cents": cfg["upgrade_cents"] if upgrade else cfg["included_cents"],
            "charge_cents": cents,
            "declared_value_cents": request.declared_value_cents,
            "recommended": rec["tier"],
            "reason": rec["reason"],
            "over_max": rec["tier"] == "over_max",
        }

    def _apply_origin_pickup(
        self,
        request: PricingRequest,
        policy: MerchantPricingPolicy,
        breakdown: PriceBreakdown,
    ) -> None:
        schedule = policy.schedule
        cents = int(schedule.origin_pickup_cents or 0)
        if cents <= 0:
            return
        allow = {str(v).lower() for v in schedule.origin_pickup_vehicle_classes}
        vehicle = str(request.vehicle_class or "").lower()
        if allow and vehicle not in allow:
            return
        breakdown.add_item("origin_pickup", "Origin pickup", cents)
        breakdown.metadata["origin_pickup_cents"] = cents

    def _apply_route_minimum(
        self,
        request: PricingRequest,
        ctx: PricingContext,
        policy: MerchantPricingPolicy,
        breakdown: PriceBreakdown,
    ) -> None:
        schedule = policy.schedule
        # Compact path has its own route minimum.
        if breakdown.metadata.get("compact_banding"):
            min_cents = int(schedule.compact.route_minimum_cents or 0)
        else:
            mins = schedule.route_minimums_cents or {}
            if not mins:
                return
            # `_apply_fsa_rate` records the matched row's tier; nothing else sets it.
            tier = breakdown.metadata.get("fsa_tier")
            if not tier or tier not in mins:
                return
            min_cents = int(mins[tier])
        if min_cents <= 0:
            return
        true_bill = sum(i.amount_cents for i in breakdown.items)
        top_up = min_cents - true_bill
        if top_up <= 0:
            return
        breakdown.add_item("route_minimum", "Route minimum", top_up)
        breakdown.metadata["route_minimum_cents"] = min_cents
        breakdown.metadata["route_minimum_top_up_cents"] = top_up

    def _apply_compact_banding(
        self,
        request: PricingRequest,
        ctx: PricingContext,
        breakdown: PriceBreakdown,
    ) -> None:
        """
        When compact schedule is on and vehicle is compact-class, replace the
        base with stop banding if dest has a compact-class FSA row (territory).
        """
        import math

        policy = ctx.merchant_policy or MerchantPricingPolicy()
        compact = policy.schedule.compact
        if not compact.enabled:
            return
        vehicle = str(request.vehicle_class or "").lower()
        classes = {str(c).lower() for c in compact.vehicle_classes}
        if vehicle not in classes:
            return

        # Territory: dest has an active FSA row for a compact-class vehicle.
        from porterchain_pricing.components.fsa import fsa_from_point

        dest = fsa_from_point(request.dropoff) if request.dropoff else ""
        if not dest:
            return
        in_territory = False
        for row in ctx.fsa_rates:
            if not row.is_active:
                continue
            if str(row.dest_fsa).upper() != dest.upper():
                continue
            vc = (row.vehicle_class or "").lower()
            if vc in classes or vc == vehicle:
                in_territory = True
                break
        if not in_territory:
            return

        parcels = max(int(request.parcel_count or 1), 1)
        billable_stops = max(1, math.ceil(parcels / max(compact.parcels_per_stop, 1)))
        band_cents = 0
        for band in sorted(
            compact.stop_rates,
            key=lambda b: (b.max_stops is None, b.max_stops or 0),
        ):
            if band.max_stops is None or billable_stops <= band.max_stops:
                band_cents = int(band.cents)
                break
        if band_cents <= 0:
            return

        # Replace prior base / FSA / GTA line items with compact stop charge.
        # Drop every geographic / distance / stop-fee line the prior base layer
        # may have added. StopFeeService emits a single "stop_fees" code (not
        # extra_pickup / extra_drop), so those must be listed explicitly.
        _COMPACT_REPLACES = {
            "fsa_rate",
            "base",
            "distance",
            "extra_km",
            "extra_pickup",
            "extra_drop",
            "stop_fees",
            "downtown",
            "upper_zone",
            "zone_multiplier",
        }
        kept = [i for i in breakdown.items if i.code not in _COMPACT_REPLACES]
        breakdown.items = kept
        breakdown.base_cents = band_cents
        breakdown.distance_cents = 0
        breakdown.add_item(
            "compact_stop",
            f"Compact delivery ({billable_stops} stop{'s' if billable_stops != 1 else ''})",
            band_cents,
        )
        breakdown.metadata["pricing_model"] = "compact_banding"
        breakdown.metadata["compact_banding"] = True
        breakdown.metadata["compact_billable_stops"] = billable_stops
        breakdown.metadata["compact_parcel_count"] = parcels

