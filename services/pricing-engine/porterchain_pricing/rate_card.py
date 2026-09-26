"""System + merchant rate card — admin-editable commercial knobs."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any

from porterchain_pricing.catalog import (
    DECLARED_VALUE_RATE,
    DECLARED_VALUE_THRESHOLD_CENTS,
    EXTRA_STOP_CENTS,
    LIFTGATE_SURCHARGE_CENTS,
    PACKAGE_SURCHARGE_CENTS,
    RUSH_SURCHARGE_CENTS,
    SCHEDULED_SURCHARGE_CENTS,
    SERVICE_SURCHARGE_CENTS,
    VEHICLE_BASE_CENTS_PER_KM,
    VEHICLE_MINIMUM_CENTS,
    VEHICLE_SURCHARGE_CENTS,
    WEIGHT_CENTS_PER_KG,
    WEIGHT_THRESHOLD_KG,
)


@dataclass
class VehicleRate:
    per_km_cents: int = 100
    minimum_cents: int = 100
    surcharge_cents: int = 0


@dataclass
class RateCard:
    """Authoritative commercial rates for quote/invoice calculation."""

    vehicles: dict[str, VehicleRate] = field(default_factory=dict)
    base_fee_cents: int = 0
    per_minute_cents: int = 0
    wait_cents_per_minute: int = 0
    extra_stop_cents: int = EXTRA_STOP_CENTS
    liftgate_cents: int = LIFTGATE_SURCHARGE_CENTS
    rush_surcharge_cents: int = RUSH_SURCHARGE_CENTS
    scheduled_surcharge_cents: int = SCHEDULED_SURCHARGE_CENTS
    weight_threshold_kg: float = float(WEIGHT_THRESHOLD_KG)
    weight_cents_per_kg: int = WEIGHT_CENTS_PER_KG
    declared_value_threshold_cents: int = DECLARED_VALUE_THRESHOLD_CENTS
    declared_value_rate: float = float(DECLARED_VALUE_RATE)
    weekend_multiplier: float = 1.0
    holiday_multiplier: float = 1.0
    holidays: list[str] = field(default_factory=list)
    night_multiplier: float = 1.0
    night_start_hour: int = 22
    night_end_hour: int = 6
    # Driver wallet credit on delivery (authoritative for EarningsService)
    # "flat" = driver_flat_per_delivery_cents; "percent" = order_amount × driver_share_pct
    driver_payout_mode: str = "flat"
    driver_flat_per_delivery_cents: int = 850
    driver_minimum_payout_cents: int = 0
    driver_share_pct: float = 72.0
    platform_share_pct: float = 28.0
    package_surcharges: dict[str, int] = field(default_factory=dict)
    service_surcharges: dict[str, int] = field(default_factory=dict)

    def vehicle(self, vehicle_class: str) -> VehicleRate:
        if vehicle_class in self.vehicles:
            return self.vehicles[vehicle_class]
        # Legacy camel card keys ↔ snake Capacity Catalog ids.
        camel = _to_camel(vehicle_class)
        if camel in self.vehicles:
            return self.vehicles[camel]
        snake = _to_snake(vehicle_class)
        if snake in self.vehicles:
            return self.vehicles[snake]
        return VehicleRate()

    def to_dict(self) -> dict[str, Any]:
        return {
            "vehicles": {k: asdict(v) for k, v in self.vehicles.items()},
            "base_fee_cents": self.base_fee_cents,
            "per_minute_cents": self.per_minute_cents,
            "wait_cents_per_minute": self.wait_cents_per_minute,
            "extra_stop_cents": self.extra_stop_cents,
            "liftgate_cents": self.liftgate_cents,
            "rush_surcharge_cents": self.rush_surcharge_cents,
            "scheduled_surcharge_cents": self.scheduled_surcharge_cents,
            "weight_threshold_kg": self.weight_threshold_kg,
            "weight_cents_per_kg": self.weight_cents_per_kg,
            "declared_value_threshold_cents": self.declared_value_threshold_cents,
            "declared_value_rate": self.declared_value_rate,
            "weekend_multiplier": self.weekend_multiplier,
            "holiday_multiplier": self.holiday_multiplier,
            "holidays": list(self.holidays),
            "night_multiplier": self.night_multiplier,
            "night_start_hour": self.night_start_hour,
            "night_end_hour": self.night_end_hour,
            "driver_payout_mode": self.driver_payout_mode,
            "driver_flat_per_delivery_cents": self.driver_flat_per_delivery_cents,
            "driver_minimum_payout_cents": self.driver_minimum_payout_cents,
            "driver_share_pct": self.driver_share_pct,
            "platform_share_pct": self.platform_share_pct,
            "package_surcharges": dict(self.package_surcharges),
            "service_surcharges": dict(self.service_surcharges),
        }

    def compute_driver_payout_cents(self, *, order_amount_cents: int | None = None) -> int:
        """Wallet credit for one completed delivery from this rate card."""
        mode = (self.driver_payout_mode or "flat").strip().lower()
        if mode == "percent":
            base = max(int(order_amount_cents or 0), 0)
            amount = int(round(base * float(self.driver_share_pct) / 100.0))
        else:
            amount = int(self.driver_flat_per_delivery_cents)
        floor = int(self.driver_minimum_payout_cents or 0)
        return max(amount, floor, 0)


def default_rate_card() -> RateCard:
    vehicles = {
        code: VehicleRate(
            per_km_cents=VEHICLE_BASE_CENTS_PER_KM.get(code, 100),
            minimum_cents=VEHICLE_MINIMUM_CENTS.get(code, 100),
            surcharge_cents=VEHICLE_SURCHARGE_CENTS.get(code, 0),
        )
        for code in VEHICLE_BASE_CENTS_PER_KM
    }
    return RateCard(
        vehicles=vehicles,
        package_surcharges={str(k): int(v) for k, v in PACKAGE_SURCHARGE_CENTS.items()},
        service_surcharges={str(k): int(v) for k, v in SERVICE_SURCHARGE_CENTS.items()},
    )


def rate_card_from_dict(data: dict[str, Any] | None, *, base: RateCard | None = None) -> RateCard:
    """Build a rate card, optionally starting from `base` then applying overlay keys."""
    card = deepcopy(base) if base is not None else default_rate_card()
    if not data:
        return card

    vehicles_raw = data.get("vehicles")
    if isinstance(vehicles_raw, dict):
        for code, row in vehicles_raw.items():
            if not isinstance(row, dict):
                continue
            existing = card.vehicles.get(code) or VehicleRate()
            card.vehicles[code] = VehicleRate(
                per_km_cents=int(row.get("per_km_cents", existing.per_km_cents)),
                minimum_cents=int(row.get("minimum_cents", existing.minimum_cents)),
                surcharge_cents=int(row.get("surcharge_cents", existing.surcharge_cents)),
            )

    for key in (
        "base_fee_cents",
        "per_minute_cents",
        "wait_cents_per_minute",
        "extra_stop_cents",
        "liftgate_cents",
        "rush_surcharge_cents",
        "scheduled_surcharge_cents",
        "weight_cents_per_kg",
        "declared_value_threshold_cents",
        "driver_flat_per_delivery_cents",
        "driver_minimum_payout_cents",
    ):
        if key in data and data[key] is not None:
            setattr(card, key, int(data[key]))

    if "weight_threshold_kg" in data and data["weight_threshold_kg"] is not None:
        card.weight_threshold_kg = float(data["weight_threshold_kg"])
    if "declared_value_rate" in data and data["declared_value_rate"] is not None:
        card.declared_value_rate = float(data["declared_value_rate"])
    if "driver_payout_mode" in data and data["driver_payout_mode"] is not None:
        mode = str(data["driver_payout_mode"]).strip().lower()
        card.driver_payout_mode = mode if mode in ("flat", "percent") else "flat"

    for key in (
        "weekend_multiplier",
        "holiday_multiplier",
        "night_multiplier",
        "driver_share_pct",
        "platform_share_pct",
    ):
        if key in data and data[key] is not None:
            setattr(card, key, float(data[key]))

    for key in ("night_start_hour", "night_end_hour"):
        if key in data and data[key] is not None:
            setattr(card, key, int(data[key]))

    if "holidays" in data and data["holidays"] is not None:
        card.holidays = [str(h) for h in data["holidays"]]

    if isinstance(data.get("package_surcharges"), dict):
        card.package_surcharges.update({str(k): int(v) for k, v in data["package_surcharges"].items()})
    if isinstance(data.get("service_surcharges"), dict):
        card.service_surcharges.update({str(k): int(v) for k, v in data["service_surcharges"].items()})

    # Backward-compat flat keys previously used in merchant.pricing_config
    if "minimum_charge_cents" in data and data["minimum_charge_cents"] is not None:
        floor = int(data["minimum_charge_cents"])
        for v in card.vehicles.values():
            v.minimum_cents = floor

    return card


def merge_merchant_overlay(system: RateCard, merchant_config: dict[str, Any] | None) -> RateCard:
    """Apply merchant `rate_card` (+ legacy flat keys) over system card."""
    cfg = dict(merchant_config or {})
    overlay = dict(cfg.get("rate_card") or {})
    # Lift legacy top-level keys into overlay when present
    for legacy in (
        "minimum_charge_cents",
        "weekend_multiplier",
        "holiday_multiplier",
        "holidays",
        "driver_share_pct",
        "margin_pct",
    ):
        if legacy in cfg and legacy not in overlay:
            if legacy == "margin_pct":
                overlay["platform_share_pct"] = cfg[legacy]
            else:
                overlay[legacy] = cfg[legacy]
    return rate_card_from_dict(overlay, base=system)


def _to_camel(value: str) -> str:
    parts = value.replace("-", "_").split("_")
    if len(parts) == 1:
        return value
    return parts[0] + "".join(p.title() for p in parts[1:])


def _to_snake(value: str) -> str:
    import re

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value or "")
    return spaced.lower().replace("-", "_")
