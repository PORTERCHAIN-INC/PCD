"""Pricing simulator — admin preview with optional rule overrides."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from porterchain_pricing.engine import PricingEngine
from porterchain_pricing.repository import PricingRepository
from porterchain_pricing.types import (
    ContractRecord,
    FuelConfig,
    PricingContext,
    PricingRequest,
    PriceBreakdown,
    PromotionRecord,
    TariffRecord,
    TaxConfig,
    ZoneRecord,
)


class PricingSimulator:
    """Preview pricing with hypothetical rules — no persistence."""

    def __init__(
        self,
        *,
        engine: PricingEngine | None = None,
        repository: PricingRepository | None = None,
    ) -> None:
        self.engine = engine or PricingEngine()
        self.repository = repository

    def simulate(
        self,
        request: PricingRequest,
        *,
        overrides: dict[str, Any] | None = None,
        base_context: PricingContext | None = None,
    ) -> PriceBreakdown:
        ctx = base_context or (self.repository.load_context(request) if self.repository else PricingContext())
        ctx = deepcopy(ctx)
        self._apply_overrides(ctx, overrides or {})
        return self.engine.calculate(request, ctx)

    def compare_scenarios(
        self,
        request: PricingRequest,
        scenarios: list[dict[str, Any]],
        *,
        base_context: PricingContext | None = None,
    ) -> list[dict[str, Any]]:
        results = []
        for scenario in scenarios:
            name = scenario.get("name", "scenario")
            overrides = scenario.get("overrides", {})
            breakdown = self.simulate(request, overrides=overrides, base_context=base_context)
            results.append({"name": name, "breakdown": breakdown})
        return results

    @staticmethod
    def _apply_overrides(ctx: PricingContext, overrides: dict[str, Any]) -> None:
        if "tax" in overrides:
            ctx.tax = TaxConfig(**overrides["tax"])
        if "fuel" in overrides:
            ctx.fuel = FuelConfig(**overrides["fuel"])
        if "tariffs" in overrides:
            ctx.tariffs = [TariffRecord(**t) for t in overrides["tariffs"]]
        if "promotions" in overrides:
            ctx.promotions = [PromotionRecord(**p) for p in overrides["promotions"]]
        if "zones" in overrides:
            ctx.zones = [ZoneRecord(**z) for z in overrides["zones"]]
        if "contract" in overrides:
            ctx.contract = ContractRecord(**overrides["contract"])
        if "merchant_pricing_config" in overrides:
            ctx.merchant_pricing_config = overrides["merchant_pricing_config"]
        if "gta_rate" in overrides:
            from porterchain_pricing.gta_rate import gta_rate_config_from_dict, merge_merchant_gta_overlay

            raw = overrides["gta_rate"]
            if isinstance(raw, dict):
                if ctx.gta_rate is not None:
                    ctx.gta_rate = merge_merchant_gta_overlay(ctx.gta_rate, {"gta_rate": raw})
                else:
                    ctx.gta_rate = gta_rate_config_from_dict(raw)
