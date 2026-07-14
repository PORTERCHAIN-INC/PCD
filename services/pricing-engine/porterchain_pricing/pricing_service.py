"""Pricing service facade — Porterchain owns all pricing logic."""

from __future__ import annotations

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
        retail_request = PricingRequest(
            pickup=request.pickup,
            dropoff=request.dropoff,
            vehicle_class=request.vehicle_class,
            package_type=request.package_type,
            service_type=request.service_type,
            weight_kg=request.weight_kg,
            dimensions=request.dimensions,
            declared_value_cents=request.declared_value_cents,
            schedule_mode=request.schedule_mode,
            scheduled_at=request.scheduled_at,
            is_rush=request.is_rush,
            additional_stops=request.additional_stops,
            distance_meters=request.distance_meters,
            estimated_duration_minutes=request.estimated_duration_minutes,
            routing_source=request.routing_source,
            channel="retail",
            promo_code=request.promo_code,
            wallet_credit_cents=request.wallet_credit_cents,
            referral_credit_cents=request.referral_credit_cents,
            wait_minutes=request.wait_minutes,
            requires_liftgate=request.requires_liftgate,
        )
        return self.calculate(retail_request)

    def calculate_merchant(self, request: PricingRequest) -> PriceBreakdown:
        merchant_request = PricingRequest(
            pickup=request.pickup,
            dropoff=request.dropoff,
            vehicle_class=request.vehicle_class,
            package_type=request.package_type,
            service_type=request.service_type,
            weight_kg=request.weight_kg,
            dimensions=request.dimensions,
            declared_value_cents=request.declared_value_cents,
            schedule_mode=request.schedule_mode,
            scheduled_at=request.scheduled_at,
            is_rush=request.is_rush,
            additional_stops=request.additional_stops,
            distance_meters=request.distance_meters,
            estimated_duration_minutes=request.estimated_duration_minutes,
            routing_source=request.routing_source,
            wait_minutes=request.wait_minutes,
            channel="merchant",
            merchant_id=request.merchant_id,
            promo_code=request.promo_code,
            volume_units=request.volume_units,
            requires_liftgate=request.requires_liftgate,
        )
        return self.calculate(merchant_request)

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
