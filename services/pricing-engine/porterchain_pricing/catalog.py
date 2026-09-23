"""Vehicle, service, and package catalogs."""

from enum import StrEnum


class VehicleClass(StrEnum):
    SEDAN = "sedan"
    SUV = "suv"
    SEDAN_SUV = "sedan_suv"
    PICKUP = "pickup"
    CARGO_VAN = "cargoVan"
    CARGO_VAN_SNAKE = "cargo_van"
    HIGH_ROOF = "highRoof"
    BOX_16 = "box16"
    BOX_16_SNAKE = "box_16"
    BOX_20 = "box20"
    BOX_20_SNAKE = "box_20"


class ServiceType(StrEnum):
    SAME_DAY = "same_day"
    EXPRESS = "express"
    SCHEDULED = "scheduled"
    RECURRING = "recurring"
    MULTI_STOP = "multi_stop"
    LTL = "ltl"
    FTL = "ftl"
    FURNITURE = "furniture"
    MEDICAL = "medical"
    CONSTRUCTION = "construction"
    WHOLESALE = "wholesale"


class PackageType(StrEnum):
    LOOSE_PARCEL = "looseParcel"
    DOCUMENTS = "documents"
    MEDICAL = "medical"
    FURNITURE = "furniture"
    FOOD_BEVERAGE = "foodBeverage"
    CONSTRUCTION = "construction"
    LTL_PALLET = "ltlPallet"
    FTL_LOAD = "ftlLoad"


# Retail defaults — CAD cents ($1.00 / km, $1.00 minimum for 1 km billed distance)
_VEHICLE_RATE_CENTS_PER_KM = 100
_VEHICLE_MINIMUM_CENTS = 100

VEHICLE_BASE_CENTS_PER_KM: dict[str, int] = {
    VehicleClass.SEDAN: _VEHICLE_RATE_CENTS_PER_KM,
    VehicleClass.SUV: _VEHICLE_RATE_CENTS_PER_KM,
    VehicleClass.PICKUP: _VEHICLE_RATE_CENTS_PER_KM,
    VehicleClass.CARGO_VAN: _VEHICLE_RATE_CENTS_PER_KM,
    VehicleClass.HIGH_ROOF: _VEHICLE_RATE_CENTS_PER_KM,
    VehicleClass.BOX_16: _VEHICLE_RATE_CENTS_PER_KM,
    VehicleClass.BOX_20: _VEHICLE_RATE_CENTS_PER_KM,
}

VEHICLE_MINIMUM_CENTS: dict[str, int] = {
    VehicleClass.SEDAN: _VEHICLE_MINIMUM_CENTS,
    VehicleClass.SUV: _VEHICLE_MINIMUM_CENTS,
    VehicleClass.PICKUP: _VEHICLE_MINIMUM_CENTS,
    VehicleClass.CARGO_VAN: _VEHICLE_MINIMUM_CENTS,
    VehicleClass.HIGH_ROOF: _VEHICLE_MINIMUM_CENTS,
    VehicleClass.BOX_16: _VEHICLE_MINIMUM_CENTS,
    VehicleClass.BOX_20: _VEHICLE_MINIMUM_CENTS,
}

VEHICLE_SURCHARGE_CENTS: dict[str, int] = {
    VehicleClass.SEDAN: 0,
    VehicleClass.SUV: 0,
    VehicleClass.PICKUP: 0,
    VehicleClass.CARGO_VAN: 0,
    VehicleClass.HIGH_ROOF: 0,
    VehicleClass.BOX_16: 0,
    VehicleClass.BOX_20: 0,
}

PACKAGE_SURCHARGE_CENTS: dict[str, int] = {
    PackageType.LOOSE_PARCEL: 0,
    PackageType.DOCUMENTS: 0,
    PackageType.MEDICAL: 0,
    PackageType.FURNITURE: 0,
    PackageType.FOOD_BEVERAGE: 0,
    PackageType.CONSTRUCTION: 0,
    PackageType.LTL_PALLET: 0,
    PackageType.FTL_LOAD: 0,
}

SERVICE_SURCHARGE_CENTS: dict[str, int] = {
    ServiceType.SAME_DAY: 0,
    ServiceType.EXPRESS: 0,
    ServiceType.SCHEDULED: 0,
    ServiceType.RECURRING: 0,
    ServiceType.MULTI_STOP: 0,
    ServiceType.LTL: 0,
    ServiceType.FTL: 0,
    ServiceType.FURNITURE: 0,
    ServiceType.MEDICAL: 0,
    ServiceType.CONSTRUCTION: 0,
    ServiceType.WHOLESALE: 0,
}

RUSH_SURCHARGE_CENTS = 0
SCHEDULED_SURCHARGE_CENTS = 0
EXTRA_STOP_CENTS = 0
LIFTGATE_SURCHARGE_CENTS = 4500  # §8.1.7 — construction jobsite liftgate service (CAD cents)
WEIGHT_THRESHOLD_KG = 50
WEIGHT_CENTS_PER_KG = 0
DIMENSION_VOLUME_THRESHOLD_CM3 = 100_000
DIMENSION_CENTS_PER_10K_CM3 = 0
DECLARED_VALUE_THRESHOLD_CENTS = 50_000
DECLARED_VALUE_RATE = 0.0
AVG_SPEED_KMH = 30.0
