"""
Size and weight component — overweight, oversize and declared value.

The thresholds have existed on the rate card since the beginning but nothing
ever read them, so setting `weight_cents_per_kg` had no effect on any price.
This is the service that charges for them. Every rate defaults to zero, so a
deployment only starts billing these once the rate card says to.
"""

from __future__ import annotations

from typing import Any

from porterchain_pricing.components.quote import ComponentQuote, _item
from porterchain_pricing.policy import SizeTier
from porterchain_pricing.rate_card import RateCard
from porterchain_pricing.types import SizeWeightConfig

COMPONENT = "size_weight"

#: Volume beyond this is billed in `cents_per_10k_cm3` blocks.
DEFAULT_VOLUME_THRESHOLD_CM3 = 100_000
_CM3_BLOCK = 10_000


def config_from_rate_card(card: RateCard) -> SizeWeightConfig:
    """Read the billing thresholds off the merged (system + merchant) rate card."""
    return SizeWeightConfig(
        weight_threshold_kg=float(card.weight_threshold_kg or 0.0),
        weight_cents_per_kg=int(card.weight_cents_per_kg or 0),
        volume_threshold_cm3=DEFAULT_VOLUME_THRESHOLD_CM3,
        cents_per_10k_cm3=0,
        declared_value_threshold_cents=int(card.declared_value_threshold_cents or 0),
        declared_value_rate=float(card.declared_value_rate or 0.0),
    )


def parse_dimensions_cm(
    dimensions: dict[str, float] | str | None,
) -> tuple[float | None, float | None, float | None]:
    """
    Length, width and height in cm from `{length, width, height}` or "LxWxH".

    Returns all-None when the input cannot be understood, so an unparseable
    dimension string never produces a size charge.
    """
    if not dimensions:
        return (None, None, None)
    if isinstance(dimensions, dict):
        out = []
        for keys in (("length", "l"), ("width", "w"), ("height", "h")):
            raw = next((dimensions.get(k) for k in keys if dimensions.get(k) is not None), None)
            try:
                out.append(float(raw) if raw is not None else None)
            except (TypeError, ValueError):
                out.append(None)
        return (out[0], out[1], out[2])

    text = str(dimensions).lower().replace(" ", "")
    for sep in ("x", "*", "×"):
        if sep in text:
            parts = text.split(sep)
            if len(parts) != 3:
                return (None, None, None)
            try:
                l, w, h = (float(p.rstrip("cm")) for p in parts)
            except (TypeError, ValueError):
                return (None, None, None)
            return (l, w, h)
    return (None, None, None)


def parse_volume_cm3(dimensions: dict[str, float] | str | None) -> float:
    """
    Volume in cm³ from `{length, width, height}` or an "LxWxH" string.

    Returns 0.0 when the input cannot be understood — an unparseable dimension
    string must never silently become a charge.
    """
    if not dimensions:
        return 0.0
    if isinstance(dimensions, dict):
        try:
            l = float(dimensions.get("length") or dimensions.get("l") or 0)
            w = float(dimensions.get("width") or dimensions.get("w") or 0)
            h = float(dimensions.get("height") or dimensions.get("h") or 0)
        except (TypeError, ValueError):
            return 0.0
        return max(l * w * h, 0.0)

    text = str(dimensions).lower().replace(" ", "")
    for sep in ("x", "*", "×"):
        if sep in text:
            parts = text.split(sep)
            if len(parts) != 3:
                return 0.0
            try:
                l, w, h = (float(p.rstrip("cm")) for p in parts)
            except (TypeError, ValueError):
                return 0.0
            return max(l * w * h, 0.0)
    return 0.0


class SizeWeightService:
    def quote_tiers(
        self,
        tiers: list[SizeTier],
        *,
        weight_kg: float | None = None,
        dimensions: dict[str, float] | str | None = None,
    ) -> ComponentQuote:
        """
        Charge the merchant's own size / weight band for this shipment.

        Rows are evaluated in the order the admin arranged them and the first
        one that fits wins, so a merchant controls precedence directly rather
        than inferring it from the numbers. A shipment that fits no row is not
        charged — a merchant who wants to catch everything adds a final row
        with no limits.
        """
        length, width, height = parse_dimensions_cm(dimensions)
        weight = float(weight_kg) if weight_kg else None

        for index, tier in enumerate(tiers):
            if not tier.accepts(
                length_cm=length, width_cm=width, height_cm=height, weight_kg=weight
            ):
                continue
            return ComponentQuote(
                component=COMPONENT,
                items=_item("size_tier", tier.describe(), tier.surcharge_cents),
                metadata={
                    "mode": "tiers",
                    "matched": True,
                    "tier_index": index,
                    "tier_label": tier.describe(),
                    "surcharge_cents": tier.surcharge_cents,
                    "shipment_cm": [length, width, height],
                    "shipment_kg": weight,
                },
            )

        return ComponentQuote(
            component=COMPONENT,
            metadata={
                "mode": "tiers",
                "matched": False,
                "reason": "no_matching_tier",
                "shipment_cm": [length, width, height],
                "shipment_kg": weight,
            },
        )

    def quote(
        self,
        *,
        weight_kg: float | None = None,
        dimensions: dict[str, float] | str | None = None,
        declared_value_cents: int | None = None,
        config: SizeWeightConfig | None = None,
    ) -> ComponentQuote:
        cfg = config or SizeWeightConfig()
        items = []
        metadata: dict[str, Any] = {}

        weight = max(float(weight_kg or 0.0), 0.0)
        billable_kg = max(weight - float(cfg.weight_threshold_kg), 0.0)
        weight_cents = int(round(billable_kg * int(cfg.weight_cents_per_kg)))
        if cfg.weight_cents_per_kg:
            items += _item("overweight", f"Overweight ({billable_kg:.1f} kg over)", weight_cents)
        metadata.update(
            {
                "weight_kg": weight,
                "weight_threshold_kg": cfg.weight_threshold_kg,
                "billable_kg": round(billable_kg, 3),
                "weight_cents": weight_cents,
            }
        )

        volume = parse_volume_cm3(dimensions)
        billable_volume = max(volume - float(cfg.volume_threshold_cm3), 0.0)
        blocks = billable_volume / _CM3_BLOCK
        volume_cents = int(round(blocks * int(cfg.cents_per_10k_cm3)))
        if cfg.cents_per_10k_cm3:
            items += _item("oversize", f"Oversize ({billable_volume/1000:.1f} L over)", volume_cents)
        metadata.update(
            {
                "volume_cm3": volume,
                "volume_threshold_cm3": cfg.volume_threshold_cm3,
                "billable_volume_cm3": round(billable_volume, 1),
                "volume_cents": volume_cents,
            }
        )

        declared = max(int(declared_value_cents or 0), 0)
        insurable = max(declared - int(cfg.declared_value_threshold_cents), 0)
        declared_cents = int(round(insurable * float(cfg.declared_value_rate)))
        if cfg.declared_value_rate:
            items += _item("declared_value", "Declared value coverage", declared_cents)
        metadata.update(
            {
                "declared_value_cents": declared,
                "declared_value_threshold_cents": cfg.declared_value_threshold_cents,
                "insurable_cents": insurable,
                "declared_value_charge_cents": declared_cents,
            }
        )

        return ComponentQuote(component=COMPONENT, items=items, metadata=metadata)
