"""PorterChain Pricing & Contract Engine — retail and merchant quotes."""

from porterchain_pricing.catalog import (
    PACKAGE_SURCHARGE_CENTS,
    SERVICE_SURCHARGE_CENTS,
    VEHICLE_BASE_CENTS_PER_KM,
    VEHICLE_MINIMUM_CENTS,
    PackageType,
    ServiceType,
    VehicleClass,
)
from porterchain_pricing.components import (
    ComponentQuote,
    DistanceRateService,
    FsaRateService,
    LocationSurchargeService,
    SizeWeightService,
    StopFeeService,
    fsa_from_point,
    is_ontario_fsa,
    normalize_fsa,
)
from porterchain_pricing.contract import ContractService
from porterchain_pricing.distance import estimate_duration_minutes, haversine_meters, total_route_meters
from porterchain_pricing.engine import PricingEngine
from porterchain_pricing.gta150_fsa import (
    gta150_fsa_codes,
    gta150_fsa_record,
    gta150_registry_meta,
    is_gta150_fsa,
    load_gta150_registry,
)
from porterchain_pricing.gta_rate import (
    VEHICLE_MATRIX,
    GtaRateConfig,
    default_gta_rate_config,
    gta_rate_config_from_dict,
    merge_merchant_gta_overlay,
    normalize_vehicle_type,
)
from porterchain_pricing.pricing_service import PricingService
from porterchain_pricing.promotion import PromotionService
from porterchain_pricing.repository import InMemoryPricingRepository, PricingRepository
from porterchain_pricing.simulator import PricingSimulator
from porterchain_pricing.tax import TaxService
from porterchain_pricing.rate_card import RateCard, VehicleRate, default_rate_card, merge_merchant_overlay, rate_card_from_dict
from porterchain_pricing.types import (
    FsaRateRecord,
    GeoPoint,
    ParcelSpec,
    PriceBreakdown,
    PriceLineItem,
    PricingContext,
    PricingRequest,
    SizeWeightConfig,
)
from porterchain_pricing.zone import ZoneService

__all__ = [
    "ComponentQuote",
    "ContractService",
    "DistanceRateService",
    "FsaRateRecord",
    "FsaRateService",
    "GeoPoint",
    "ParcelSpec",
    "LocationSurchargeService",
    "SizeWeightConfig",
    "SizeWeightService",
    "StopFeeService",
    "fsa_from_point",
    "gta150_fsa_codes",
    "gta150_fsa_record",
    "gta150_registry_meta",
    "is_gta150_fsa",
    "is_ontario_fsa",
    "load_gta150_registry",
    "normalize_fsa",
    "InMemoryPricingRepository",
    "PackageType",
    "PriceBreakdown",
    "PriceLineItem",
    "PricingContext",
    "PricingEngine",
    "PricingRepository",
    "PricingRequest",
    "PricingService",
    "PricingSimulator",
    "PromotionService",
    "RateCard",
    "ServiceType",
    "TaxService",
    "GtaRateConfig",
    "VEHICLE_MATRIX",
    "VehicleClass",
    "VehicleRate",
    "ZoneService",
    "default_gta_rate_config",
    "default_rate_card",
    "estimate_duration_minutes",
    "gta_rate_config_from_dict",
    "haversine_meters",
    "merge_merchant_gta_overlay",
    "merge_merchant_overlay",
    "normalize_vehicle_type",
    "rate_card_from_dict",
    "total_route_meters",
]
