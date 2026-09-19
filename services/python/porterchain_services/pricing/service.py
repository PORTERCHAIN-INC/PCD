"""Pricing service — delegates to porterchain_pricing engine."""

from typing import Any

from porterchain_pricing import GeoPoint, PricingRequest, PricingService as CorePricingService
from porterchain_services.base import BaseService


class PricingService(BaseService):
    service_name = "pricing"
    _core: CorePricingService | None = None

    def register_core(self, core: CorePricingService) -> None:
        self._core = core

    @property
    def core(self) -> CorePricingService:
        if self._core is None:
            self._core = CorePricingService()
        return self._core

    def calculate(
        self,
        *,
        vehicle_class: str,
        package_type: str,
        distance_meters: int | None,
        weight_kg: float | None,
        schedule_mode: str,
        pickup_lat: float | None = None,
        pickup_lng: float | None = None,
        dropoff_lat: float | None = None,
        dropoff_lng: float | None = None,
        merchant_id: str | None = None,
    ) -> tuple[int, list[dict[str, Any]]]:
        request = PricingRequest(
            pickup=GeoPoint(lat=pickup_lat, lng=pickup_lng),
            dropoff=GeoPoint(lat=dropoff_lat, lng=dropoff_lng),
            vehicle_class=vehicle_class,
            package_type=package_type,
            service_type="scheduled" if schedule_mode == "later" else "same_day",
            weight_kg=weight_kg,
            schedule_mode=schedule_mode,
            is_rush=schedule_mode == "now",
            distance_meters=distance_meters,
            channel="merchant" if merchant_id else "retail",
            merchant_id=merchant_id,
        )
        breakdown = (
            self.core.calculate_merchant(request) if merchant_id else self.core.calculate_retail(request)
        )
        items = [{"code": i.code, "label": i.label, "amount_cents": i.amount_cents} for i in breakdown.items]
        return breakdown.final_cents, items
