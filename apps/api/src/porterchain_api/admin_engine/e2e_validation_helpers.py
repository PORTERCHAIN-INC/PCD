"""Shared types and fixtures for E2E validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from porterchain_api.admin_engine.e2e_validation_catalog import ValidationStatus
from porterchain_api.schemas import AddressInput, WebsitePricingSnapshot

PICKUP = AddressInput(
    formatted="100 King St W, Toronto ON M5H 1A1",
    lat=43.6488,
    lng=-79.3817,
    postal="M5H 1A1",
)
DROPOFF = AddressInput(
    formatted="200 Queen St W, Toronto ON M5V 1Z2",
    lat=43.6479,
    lng=-79.3957,
    postal="M5V 1Z2",
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _website_pricing() -> WebsitePricingSnapshot:
    return WebsitePricingSnapshot(
        customer_price_cad=42.50,
        driver_payout_cad=28.0,
        platform_margin_cad=14.50,
        distance_km=5.2,
        duration_minutes=35.0,
        engine_vehicle_id="cargo_van",
        breakdown={
            "baseFee": 12.0,
            "distanceFee": 18.0,
            "fuelFee": 2.5,
            "subtotal": 32.5,
            "adjustedCost": 32.5,
            "trafficMultiplier": 1.0,
            "marginMultiplier": 1.18,
        },
        traffic={"level": "normal"},
    )


@dataclass
class StepResult:
    step: str
    status: ValidationStatus
    layer: str
    root_cause: str = ""
    recommended_fix: str = ""
    priority: str = "P3"
    duration_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "status": self.status,
            "layer": self.layer,
            "root_cause": self.root_cause,
            "recommended_fix": self.recommended_fix,
            "priority": self.priority,
            "duration_ms": round(self.duration_ms, 1),
            "details": self.details,
        }


__all__ = ["StepResult", "PICKUP", "DROPOFF", "_now_iso", "_website_pricing"]
