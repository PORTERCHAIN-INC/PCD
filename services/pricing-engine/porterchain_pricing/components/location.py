"""
Location surcharge component — downtown Toronto and Markham / North York.

Each fee applies at most once per trip no matter how many stops fall in the
area. Callers may pass the flags explicitly; otherwise they are detected from
the stop coordinates and address text.
"""

from __future__ import annotations

from porterchain_pricing.components.quote import ComponentQuote, _item
from porterchain_pricing.gta_rate import (
    GtaRateConfig,
    default_gta_rate_config,
    detect_location_flags,
)
from porterchain_pricing.types import GeoPoint

COMPONENT = "location_surcharges"


class LocationSurchargeService:
    def resolve_flags(
        self,
        *,
        pickup: GeoPoint | None = None,
        dropoff: GeoPoint | None = None,
        additional_stops: list[GeoPoint] | None = None,
        is_downtown: bool | None = None,
        is_upper_zone: bool | None = None,
    ) -> tuple[bool, bool]:
        """Explicit flags win; anything left as None is detected from the stops."""
        if is_downtown is not None and is_upper_zone is not None:
            return bool(is_downtown), bool(is_upper_zone)
        detected_downtown, detected_upper = detect_location_flags(
            pickup or GeoPoint(), dropoff or GeoPoint(), additional_stops or []
        )
        return (
            detected_downtown if is_downtown is None else bool(is_downtown),
            detected_upper if is_upper_zone is None else bool(is_upper_zone),
        )

    def quote(
        self,
        *,
        pickup: GeoPoint | None = None,
        dropoff: GeoPoint | None = None,
        additional_stops: list[GeoPoint] | None = None,
        is_downtown: bool | None = None,
        is_upper_zone: bool | None = None,
        config: GtaRateConfig | None = None,
    ) -> ComponentQuote:
        cfg = config or default_gta_rate_config()
        downtown, upper = self.resolve_flags(
            pickup=pickup,
            dropoff=dropoff,
            additional_stops=additional_stops,
            is_downtown=is_downtown,
            is_upper_zone=is_upper_zone,
        )

        downtown_cents = int(round(float(cfg.downtown_fee_cad) * 100)) if downtown else 0
        upper_cents = int(round(float(cfg.upper_zone_fee_cad) * 100)) if upper else 0

        items = _item("downtown", "Downtown Toronto surcharge", downtown_cents)
        items += _item("upper_zone", "Markham / North York surcharge", upper_cents)

        return ComponentQuote(
            component=COMPONENT,
            items=items,
            metadata={
                "is_downtown": downtown,
                "is_upper_zone": upper,
                "downtown_fee_cents": downtown_cents,
                "upper_zone_fee_cents": upper_cents,
            },
        )
