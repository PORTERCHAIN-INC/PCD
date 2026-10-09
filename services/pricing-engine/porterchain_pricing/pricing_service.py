"""Pricing service facade — Porterchain owns all pricing logic."""

from __future__ import annotations

from dataclasses import replace

from porterchain_pricing.engine import PricingEngine
from porterchain_pricing.repository import InMemoryPricingRepository, PricingRepository
from porterchain_pricing.simulator import PricingSimulator
from porterchain_pricing.types import PriceBreakdown, PriceLineItem, PricingContext, PricingRequest


class PricingService:
    """Main entry for quote and booking price calculation."""

    def __init__(
        self,
        *,
        engine: PricingEngine | None = None,
        repository: PricingRepository | None = None,
    ) -> None:
        self.engine = engine or PricingEngine()
        self.repository = repository or InMemoryPricingRepository()
        self.simulator = PricingSimulator(engine=self.engine, repository=self.repository)

    def calculate(self, request: PricingRequest, *, context: PricingContext | None = None) -> PriceBreakdown:
        ctx = context or self.repository.load_context(request)
        return self.engine.calculate(request, ctx)

    def calculate_retail(self, request: PricingRequest) -> PriceBreakdown:
        return self.calculate(replace(request, channel="retail", merchant_id=None))

    def calculate_merchant(self, request: PricingRequest) -> PriceBreakdown:
        return self.calculate(replace(request, channel="merchant"))

    @staticmethod
    def to_line_items(breakdown: PriceBreakdown) -> list[PriceLineItem]:
        return list(breakdown.items)

    @staticmethod
    def to_api_breakdown(breakdown: PriceBreakdown) -> dict:
        return {
            "base_cents": breakdown.base_cents,
            "distance_cents": breakdown.distance_cents,
            "vehicle_cents": breakdown.vehicle_cents,
            "weight_cents": breakdown.weight_cents,
            "fuel_cents": breakdown.fuel_cents,
            "tax_cents": breakdown.tax_cents,
            "discount_cents": breakdown.discount_cents,
            "subtotal_cents": breakdown.subtotal_cents,
            "final_cents": breakdown.final_cents,
            "currency": breakdown.currency,
            "zone_code": breakdown.zone_code,
            "contract_id": breakdown.contract_id,
            "promo_code": breakdown.promo_code,
            "items": [{"code": i.code, "label": i.label, "amount_cents": i.amount_cents} for i in breakdown.items],
            "metadata": breakdown.metadata,
        }
