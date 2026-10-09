"""
Distance component — base fare covering the first N km, then a per-km rate.

Distance component of the GTA matrix so a route can price distance on
its own without pulling in stop fees or location surcharges.
"""

from __future__ import annotations

from porterchain_pricing.components.quote import ComponentQuote, _item
from porterchain_pricing.gta_rate import GtaRateConfig, default_gta_rate_config, normalize_vehicle_type

COMPONENT = "distance"


class DistanceRateService:
    def quote(
        self,
        *,
        vehicle_type: str,
        total_km: float,
        config: GtaRateConfig | None = None,
    ) -> ComponentQuote:
        cfg = config or default_gta_rate_config()
        matrix_key = normalize_vehicle_type(vehicle_type, known=cfg.vehicles)
        rates = cfg.vehicle(matrix_key)

        km = max(float(total_km), 0.0)
        included_km = float(cfg.base_km_limit)
        extra_km = max(km - included_km, 0.0)

        base_cad = float(rates["base_price"])
        extra_cad = extra_km * float(rates["extra_km_rate"])

        base_cents = int(round(base_cad * 100))
        extra_cents = int(round(extra_cad * 100))

        pretty = matrix_key.replace("_", " ").title()
        items = _item("base", f"{pretty} · up to {included_km:g} km base", base_cents)
        items += _item("extra_km", f"Extra distance ({extra_km:.1f} km)", extra_cents)

        return ComponentQuote(
            component=COMPONENT,
            items=items,
            metadata={
                "vehicle_type": matrix_key,
                "total_km": km,
                "included_km": included_km,
                "extra_km": round(extra_km, 3),
                "base_price_cad": base_cad,
                "extra_km_rate_cad": float(rates["extra_km_rate"]),
                # Combined figure the GTA matrix reports as `distance_cost`.
                "distance_cost_cents": base_cents + extra_cents,
            },
        )
