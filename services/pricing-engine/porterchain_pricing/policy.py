"""
Per-merchant pricing policy, parsed out of `merchants.pricing_config`.

Three things a merchant can be set up with, independently of the platform
defaults: which model prices the trip, whether the geographic surcharges apply
to them, and a table of size / weight bands that add a surcharge.

Everything here is parsed defensively — `pricing_config` is a free-form JSON
column that predates this module, so a malformed value must degrade to the
platform default rather than break a quote.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: How the base price is chosen for this merchant.
MODEL_AUTO = "auto"
MODEL_DISTANCE = "distance"
MODEL_FSA = "fsa"
PRICING_MODELS = (MODEL_AUTO, MODEL_DISTANCE, MODEL_FSA)

#: Admins enter tier limits in whatever unit they think in; we bill in cm / kg.
CM_PER_UNIT = {"cm": 1.0, "in": 2.54, "ft": 30.48}
KG_PER_UNIT = {"kg": 1.0, "lb": 0.45359237}

DIMENSION_UNITS = tuple(CM_PER_UNIT)
WEIGHT_UNITS = tuple(KG_PER_UNIT)


def _f(value: Any) -> float | None:
    """Positive float, or None when blank / unparseable. Blank means no limit."""
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out >= 0 else None


def _i(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _b(value: Any, default: bool) -> bool:
    return default if value is None else bool(value)


@dataclass
class SizeTier:
    """
    One row of a merchant's size / weight table.

    A limit left blank is unbounded, so a row with every limit blank is a
    catch-all. Limits are stored in the unit the admin typed them in and
    converted at quote time, so nothing is lost to rounding on the way back
    into the form.
    """

    surcharge_cents: int = 0
    label: str = ""
    max_length: float | None = None
    max_width: float | None = None
    max_height: float | None = None
    dimension_unit: str = "cm"
    max_weight: float | None = None
    weight_unit: str = "kg"

    def _to_cm(self, value: float | None) -> float | None:
        if value is None:
            return None
        return value * CM_PER_UNIT.get(self.dimension_unit, 1.0)

    def limits_cm(self) -> tuple[float | None, float | None, float | None]:
        return (self._to_cm(self.max_length), self._to_cm(self.max_width), self._to_cm(self.max_height))

    def limit_kg(self) -> float | None:
        if self.max_weight is None:
            return None
        return self.max_weight * KG_PER_UNIT.get(self.weight_unit, 1.0)

    def accepts(
        self,
        *,
        length_cm: float | None,
        width_cm: float | None,
        height_cm: float | None,
        weight_kg: float | None,
    ) -> bool:
        """
        True when the shipment fits inside every limit this row sets.

        An unknown shipment value cannot violate a limit — we do not charge an
        oversize fee because a dimension was left off the booking.
        """
        for limit, actual in zip(self.limits_cm(), (length_cm, width_cm, height_cm)):
            if limit is not None and actual is not None and actual > limit:
                return False
        weight_limit = self.limit_kg()
        if weight_limit is not None and weight_kg is not None and weight_kg > weight_limit:
            return False
        return True

    def describe(self) -> str:
        if self.label:
            return self.label
        dims = [d for d in (self.max_length, self.max_width, self.max_height) if d is not None]
        parts = []
        if dims:
            parts.append("×".join(f"{d:g}" for d in dims) + f" {self.dimension_unit}")
        if self.max_weight is not None:
            parts.append(f"{self.max_weight:g} {self.weight_unit}")
        return "Up to " + ", ".join(parts) if parts else "Any size"

    def to_dict(self) -> dict[str, Any]:
        return {
            "surcharge_cents": self.surcharge_cents,
            "label": self.label,
            "max_length": self.max_length,
            "max_width": self.max_width,
            "max_height": self.max_height,
            "dimension_unit": self.dimension_unit,
            "max_weight": self.max_weight,
            "weight_unit": self.weight_unit,
        }


def size_tier_from_dict(raw: Any) -> SizeTier | None:
    if not isinstance(raw, dict):
        return None
    dimension_unit = str(raw.get("dimension_unit") or "cm").lower()
    weight_unit = str(raw.get("weight_unit") or "kg").lower()
    return SizeTier(
        surcharge_cents=max(_i(raw.get("surcharge_cents")), 0),
        label=str(raw.get("label") or ""),
        max_length=_f(raw.get("max_length")),
        max_width=_f(raw.get("max_width")),
        max_height=_f(raw.get("max_height")),
        dimension_unit=dimension_unit if dimension_unit in CM_PER_UNIT else "cm",
        max_weight=_f(raw.get("max_weight")),
        weight_unit=weight_unit if weight_unit in KG_PER_UNIT else "kg",
    )


@dataclass
class MerchantPricingPolicy:
    """Platform defaults until a merchant is configured otherwise."""

    pricing_model: str = MODEL_AUTO
    charge_downtown: bool = True
    charge_upper_zone: bool = True
    size_tiers: list[SizeTier] = field(default_factory=list)

    @property
    def suppresses_location_fees(self) -> bool:
        return not (self.charge_downtown and self.charge_upper_zone)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pricing_model": self.pricing_model,
            "surcharges": {
                "downtown": self.charge_downtown,
                "upper_zone": self.charge_upper_zone,
            },
            "size_tiers": [t.to_dict() for t in self.size_tiers],
        }


def policy_from_config(config: dict[str, Any] | None) -> MerchantPricingPolicy:
    """Read the policy out of a merchant's `pricing_config`, ignoring junk."""
    cfg = config if isinstance(config, dict) else {}

    model = str(cfg.get("pricing_model") or MODEL_AUTO).lower()
    surcharges = cfg.get("surcharges")
    surcharges = surcharges if isinstance(surcharges, dict) else {}

    tiers_raw = cfg.get("size_tiers")
    tiers = [t for t in (size_tier_from_dict(r) for r in tiers_raw) if t] if isinstance(tiers_raw, list) else []

    return MerchantPricingPolicy(
        pricing_model=model if model in PRICING_MODELS else MODEL_AUTO,
        charge_downtown=_b(surcharges.get("downtown"), True),
        charge_upper_zone=_b(surcharges.get("upper_zone"), True),
        size_tiers=tiers,
    )
