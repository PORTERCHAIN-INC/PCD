import {
  FleetBand,
  MerchantVehicleClass,
  type MerchantVehicleClass as VehicleClassId,
  type Parcel,
} from "./types";
import {
  CAPACITY_CATALOG_FALLBACK,
  canonicalizeCapacityClassId,
  type CapacityCatalogRow,
} from "../capacity-catalog";
import { convertToCm, parcelVolumeCm3, sumChargeableWeightKg } from "./units";

type PackVehicle = CapacityCatalogRow & {
  band: FleetBand;
  bandLabel: string;
};

/** Packing table driven by Capacity Catalog fallback (SoT1 dims). */
const VEHICLES: PackVehicle[] = CAPACITY_CATALOG_FALLBACK.map((row) => ({
  ...row,
  band:
    row.band === "sedan"
      ? FleetBand.SEDAN
      : row.band === "cargo_van"
        ? FleetBand.CARGO_VAN
        : FleetBand.BOX_TRUCK,
  bandLabel: row.bandLabel,
}));

const PACKING_FACTOR = 0.85;

export const VEHICLE_CHOICES: Array<{ id: VehicleClassId; label: string }> = VEHICLES.map(
  (vehicle) => ({
    id: vehicle.id as VehicleClassId,
    label: vehicle.label,
  })
);

export type VehicleRequest = "auto" | VehicleClassId | string;

export interface VehicleAllocation {
  band: FleetBand;
  bandLabel: string;
  vehicleClass: VehicleClassId;
  vehicleLabel: string;
  chargeableWeightKg: number;
  blocked: boolean;
  requestedByMerchant: boolean;
  message: string;
}

export function allocateVehicle(
  parcels: Parcel[],
  options?: { requested?: VehicleRequest; constructionSite?: boolean }
): VehicleAllocation {
  return resolveVehicle(parcels, options);
}

export function resolveVehicle(
  parcels: Parcel[],
  options?: { requested?: VehicleRequest; constructionSite?: boolean }
): VehicleAllocation {
  const requestedRaw = options?.requested ?? "auto";
  const requested =
    requestedRaw === "auto" ? "auto" : canonicalizeCapacityClassId(String(requestedRaw));
  const constructionSite = Boolean(options?.constructionSite);
  const chargeableWeightKg = sumChargeableWeightKg(parcels);
  const sized = parcels.filter(hasCompleteSize);

  if (parcels.length === 0 || (chargeableWeightKg <= 0 && sized.length === 0)) {
    return result({
      vehicle: vehicleById(MerchantVehicleClass.CARGO_VAN),
      chargeableWeightKg,
      blocked: false,
      requestedByMerchant: requested !== "auto",
      message: constructionSite
        ? "Construction site selected. A cargo van with liftgate will be used. Add parcel size and weight to confirm it fits."
        : "Add parcel size and weight. A sedan is used only when every parcel fits a trunk.",
    });
  }

  if (requested !== "auto") {
    const chosen = vehicleById(requested);
    const unfit = unfitReason(parcels, chosen, chargeableWeightKg, constructionSite);
    if (unfit) {
      return result({
        vehicle: chosen,
        chargeableWeightKg,
        blocked: true,
        requestedByMerchant: true,
        message: unfit,
      });
    }
    return result({
      vehicle: chosen,
      chargeableWeightKg,
      blocked: false,
      requestedByMerchant: true,
      message: `${chosen.label} selected. Quote uses this vehicle, distance, and stops.`,
    });
  }

  const recommended = VEHICLES.find(
    (vehicle) => !unfitReason(parcels, vehicle, chargeableWeightKg, constructionSite)
  );
  if (!recommended) {
    return result({
      vehicle: vehicleById(MerchantVehicleClass.BOX_20),
      chargeableWeightKg,
      blocked: true,
      requestedByMerchant: false,
      message:
        "No vehicle can take this cargo. A parcel exceeds box-truck size or 4500 kg. Split the route or reduce the largest item.",
    });
  }

  const why = recommendationReason(parcels, recommended, constructionSite);
  return result({
    vehicle: recommended,
    chargeableWeightKg,
    blocked: false,
    requestedByMerchant: false,
    message: why,
  });
}

function recommendationReason(
  parcels: Parcel[],
  vehicle: PackVehicle,
  constructionSite: boolean
): string {
  if (constructionSite && vehicle.id === MerchantVehicleClass.CARGO_VAN) {
    return "Construction site. Cargo van with liftgate will be dispatched. Choose a larger vehicle if you need one.";
  }
  const sedan = vehicleById(MerchantVehicleClass.SEDAN_SUV);
  if (vehicle.id !== MerchantVehicleClass.SEDAN_SUV && !fits(parcels, sedan)) {
    return `${vehicle.label} will be dispatched. Parcel size or weight does not fit a sedan.`;
  }
  if (!parcels.every(hasCompleteSize)) {
    return `${vehicle.label} will be dispatched. Enter length, width, and height before a sedan can be considered.`;
  }
  return `${vehicle.label} will be dispatched. Quote uses this vehicle, distance, and stops.`;
}

function unfitReason(
  parcels: Parcel[],
  vehicle: PackVehicle,
  chargeableWeightKg: number,
  constructionSite: boolean
): string | null {
  if (constructionSite && (vehicle.passenger || vehicle.id === MerchantVehicleClass.PICKUP)) {
    return "Construction site deliveries use a cargo van or larger, with a liftgate.";
  }
  if (chargeableWeightKg > vehicle.capacityKg) {
    return `${vehicle.label} capacity is ${vehicle.capacityKg} kg. This route is ${chargeableWeightKg} kg chargeable.`;
  }
  if (vehicle.passenger && parcels.some((parcel) => !hasCompleteSize(parcel))) {
    return `${vehicle.label} needs length, width, and height on every parcel before it can be assigned.`;
  }
  for (const parcel of parcels) {
    if (!hasCompleteSize(parcel)) continue;
    if (!parcelFitsBay(parcel, vehicle.bayCm)) {
      const sides = parcelSidesCm(parcel)
        .map((value) => `${value} cm`)
        .join(" × ");
      const bay = [...vehicle.bayCm].sort((a, b) => b - a).join(" × ");
      const name = parcel.name || parcel.sku || "A parcel";
      return `${name} is ${sides}, which does not fit a ${vehicle.label.toLowerCase()} (${bay} cm).`;
    }
  }
  const known = parcels.filter(hasCompleteSize);
  if (known.length === parcels.length && known.length > 0) {
    const volume = known.reduce((sum, parcel) => sum + parcelVolumeCm3(parcel), 0);
    const bayVolume = vehicle.bayCm[0] * vehicle.bayCm[1] * vehicle.bayCm[2] * PACKING_FACTOR;
    if (volume > bayVolume) {
      return `Combined parcel volume does not fit a ${vehicle.label.toLowerCase()}. Choose a larger vehicle.`;
    }
  }
  return null;
}

function fits(parcels: Parcel[], vehicle: PackVehicle): boolean {
  return unfitReason(parcels, vehicle, sumChargeableWeightKg(parcels), false) === null;
}

function hasCompleteSize(parcel: Parcel): boolean {
  return parcel.length > 0 && parcel.width > 0 && parcel.height > 0;
}

function parcelSidesCm(parcel: Parcel): [number, number, number] {
  return [parcel.length, parcel.width, parcel.height]
    .map((value) => convertToCm(value, parcel.dimensionsUnit))
    .sort((a, b) => b - a) as [number, number, number];
}

function parcelFitsBay(parcel: Parcel, bayCm: [number, number, number]): boolean {
  const sides = parcelSidesCm(parcel);
  const bay = [...bayCm].sort((a, b) => b - a);
  return sides[0] <= bay[0] && sides[1] <= bay[1] && sides[2] <= bay[2];
}

function vehicleById(id: string): PackVehicle {
  const cid = canonicalizeCapacityClassId(id);
  return (
    VEHICLES.find((vehicle) => vehicle.id === cid) ||
    VEHICLES.find((vehicle) => vehicle.id === MerchantVehicleClass.CARGO_VAN) ||
    VEHICLES[0]
  );
}

function result(input: {
  vehicle: PackVehicle;
  chargeableWeightKg: number;
  blocked: boolean;
  requestedByMerchant: boolean;
  message: string;
}): VehicleAllocation {
  return {
    band: input.blocked ? FleetBand.OVER_CAPACITY : input.vehicle.band,
    bandLabel: input.vehicle.bandLabel,
    vehicleClass: input.vehicle.id as VehicleClassId,
    vehicleLabel: input.vehicle.label,
    chargeableWeightKg: input.chargeableWeightKg,
    blocked: input.blocked,
    requestedByMerchant: input.requestedByMerchant,
    message: input.message,
  };
}
