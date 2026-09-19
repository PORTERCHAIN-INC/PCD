"""
Independently priced delivery components.

Each service prices one element of a delivery and returns a `ComponentQuote`,
so a caller can compose only the elements a given route needs instead of going
through the whole engine. `PricingEngine` itself is built from these, so a
component quoted on its own always agrees with the same component inside a
full quote.
"""

from porterchain_pricing.components.distance import DistanceRateService
from porterchain_pricing.components.fsa import (
    FsaRateService,
    ONTARIO_FSA_PREFIXES,
    fsa_from_point,
    is_ontario_fsa,
    normalize_fsa,
)
from porterchain_pricing.components.location import LocationSurchargeService
from porterchain_pricing.components.quote import ComponentQuote
from porterchain_pricing.components.size_weight import (
    SizeWeightService,
    config_from_rate_card,
    parse_volume_cm3,
)
from porterchain_pricing.components.stops import StopFeeService

__all__ = [
    "ComponentQuote",
    "DistanceRateService",
    "FsaRateService",
    "LocationSurchargeService",
    "ONTARIO_FSA_PREFIXES",
    "SizeWeightService",
    "StopFeeService",
    "config_from_rate_card",
    "fsa_from_point",
    "is_ontario_fsa",
    "normalize_fsa",
    "parse_volume_cm3",
]
