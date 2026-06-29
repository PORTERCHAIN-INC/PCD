"""Vehicle, service, and package catalogs."""

from enum import StrEnum


class VehicleClass(StrEnum):
    SEDAN = "sedan"
    SUV = "suv"
    PICKUP = "pickup"
    CARGO_VAN = "cargoVan"
    HIGH_ROOF = "highRoof"
    BOX_16 = "box16"
    BOX_20 = "box20"


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


# Retail defaults — CAD cents
VEHICLE_BASE_CENTS_PER_KM: dict[str, int] = {
    VehicleClass.SEDAN: 95,
    VehicleClass.SUV: 110,
    VehicleClass.PICKUP: 125,
    VehicleClass.CARGO_VAN: 145,
    VehicleClass.HIGH_ROOF: 165,
    VehicleClass.BOX_16: 195,
    VehicleClass.BOX_20: 220,
}

VEHICLE_MINIMUM_CENTS: dict[str, int] = {
    VehicleClass.SEDAN: 1999,
    VehicleClass.SUV: 2499,
    VehicleClass.PICKUP: 2799,
    VehicleClass.CARGO_VAN: 3499,
    VehicleClass.HIGH_ROOF: 3999,
    VehicleClass.BOX_16: 4999,
    VehicleClass.BOX_20: 5999,
}

VEHICLE_SURCHARGE_CENTS: dict[str, int] = {
    VehicleClass.SEDAN: 0,
    VehicleClass.SUV: 200,
    VehicleClass.PICKUP: 350,
    VehicleClass.CARGO_VAN: 500,
    VehicleClass.HIGH_ROOF: 750,
    VehicleClass.BOX_16: 1200,
    VehicleClass.BOX_20: 1500,
}

PACKAGE_SURCHARGE_CENTS: dict[str, int] = {
    PackageType.LOOSE_PARCEL: 0,
    PackageType.DOCUMENTS: 0,
    PackageType.MEDICAL: 500,
    PackageType.FURNITURE: 800,
    PackageType.FOOD_BEVERAGE: 400,
    PackageType.CONSTRUCTION: 600,
    PackageType.LTL_PALLET: 1200,
    PackageType.FTL_LOAD: 2500,
}

SERVICE_SURCHARGE_CENTS: dict[str, int] = {
    ServiceType.SAME_DAY: 0,
    ServiceType.EXPRESS: 800,
    ServiceType.SCHEDULED: 300,
    ServiceType.RECURRING: -200,
    ServiceType.MULTI_STOP: 0,
    ServiceType.LTL: 1500,
    ServiceType.FTL: 3500,
    ServiceType.FURNITURE: 600,
    ServiceType.MEDICAL: 700,
    ServiceType.CONSTRUCTION: 500,
    ServiceType.WHOLESALE: 400,
}

RUSH_SURCHARGE_CENTS = 1200
SCHEDULED_SURCHARGE_CENTS = 300
EXTRA_STOP_CENTS = 800
WEIGHT_THRESHOLD_KG = 50
WEIGHT_CENTS_PER_KG = 20
DIMENSION_VOLUME_THRESHOLD_CM3 = 100_000
DIMENSION_CENTS_PER_10K_CM3 = 150
DECLARED_VALUE_THRESHOLD_CENTS = 50_000
DECLARED_VALUE_RATE = 0.01
AVG_SPEED_KMH = 30.0
