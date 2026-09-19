"""
Stop-fee component — charges for pickups and drops beyond the first of each.

The first pickup and first drop are covered by the distance component's base
fare, so only the extras are billed here.
"""

from __future__ import annotations

from porterchain_pricing.components.quote import ComponentQuote, _item
from porterchain_pricing.gta_rate import GtaRateConfig, default_gta_rate_config, normalize_vehicle_type

COMPONENT = "stop_fees"


class StopFeeService:
    def quote(
        self,
        *,
        vehicle_type: str,
        total_pickups: int = 1,
        total_drops: int = 1,
        config: GtaRateConfig | None = None,
    ) -> ComponentQuote:
        cfg = config or default_gta_rate_config()
        matrix_key = normalize_vehicle_type(vehicle_type, known=cfg.vehicles)
        rates = cfg.vehicle(matrix_key)

        pickups = max(int(total_pickups), 1)
        drops = max(int(total_drops), 1)
        extra_pickups = pickups - 1
        extra_drops = drops - 1

        pickup_cad = extra_pickups * float(rates["extra_pick_fee"])
        drop_cad = extra_drops * float(rates["extra_drop_fee"])
        pickup_cents = int(round(pickup_cad * 100))
        drop_cents = int(round(drop_cad * 100))

        # One combined line matching the label the quote UI already renders.
        parts = []
        if extra_pickups:
            parts.append(f"{extra_pickups} extra pickup(s)")
        if extra_drops:
            parts.append(f"{extra_drops} extra drop(s)")
        label = "Multi-stop fees (" + ", ".join(parts) + ")" if parts else "Multi-stop fees"

        return ComponentQuote(
            component=COMPONENT,
            items=_item("stop_fees", label, pickup_cents + drop_cents),
            metadata={
                "vehicle_type": matrix_key,
                "total_pickups": pickups,
                "total_drops": drops,
                "extra_pickups": extra_pickups,
                "extra_drops": extra_drops,
                "extra_pick_fee_cad": float(rates["extra_pick_fee"]),
                "extra_drop_fee_cad": float(rates["extra_drop_fee"]),
                "pickup_fees_cents": pickup_cents,
                "drop_fees_cents": drop_cents,
            },
        )
