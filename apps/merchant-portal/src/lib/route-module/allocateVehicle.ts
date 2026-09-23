import {
  FleetBand,
  MerchantVehicleClass,
  type MerchantVehicleClass as VehicleClassId,
  type Parcel,
} from "./types";
import { convertToCm, parcelVolumeCm3, sumChargeableWeightKg } from "./units";

/** Cargo bay in centimetres. A parcel may be rotated; it must fit all three sides. */
const VEHICLES: Array<{
  id: VehicleClassId;
  label: string;
  band: FleetBand;
  bandLabel: string;
  capacityKg: number;
  bayCm: [number, number, number];
  passenger: boolean;
}> = [
  {
    id: MerchantVehicleClass.SEDAN,
    label: "Sedan",
    band: FleetBand.SEDAN,
    bandLabel: "Sedan",
    capacityKg: 50,
    bayCm: [110, 70, 45],
    passenger: true,
  },
  {
    id: MerchantVehicleClass.SUV,
    label: "SUV",
    band: FleetBand.SEDAN,
    bandLabel: "Sedan",
    capacityKg: 80,
    bayCm: [140, 100, 70],
    passenger: true,
  },
  {
    id: MerchantVehicleClass.PICKUP,
    label: "Pickup",
    band: FleetBand.SEDAN,
    bandLabel: "Sedan",
    capacityKg: 500,
    bayCm: [180, 150, 80],
    passenger: false,
  },
  {
    id: MerchantVehicleClass.CARGO_VAN,
    label: "Cargo van",
    band: FleetBand.CARGO_VAN,
    bandLabel: "Cargo van",
    capacityKg: 900,
    bayCm: [300, 170, 140],
    passenger: false,
  },
  {
    id: MerchantVehicleClass.HIGH_ROOF,
    label: "High-roof van",
    band: FleetBand.CARGO_VAN,
    bandLabel: "Cargo van",
    capacityKg: 1200,
    bayCm: [340, 170, 180],
    passenger: false,
  },
  {
    id: MerchantVehicleClass.BOX_16,
    label: "16 ft box truck",
    band: FleetBand.BOX_TRUCK,
    bandLabel: "Box truck",
    capacityKg: 3000,
    bayCm: [480, 245, 220],
    passenger: false,
  },
  {
    id: MerchantVehicleClass.BOX_20,
    label: "20 ft box truck",
    band: FleetBand.BOX_TRUCK,
    bandLabel: "Box truck",
    capacityKg: 4500,
    bayCm: [610, 245, 240],
    passenger: false,
  },
];

const PACKING_FACTOR = 0.85;

export const VEHICLE_CHOICES: Array<{ id: VehicleClassId; label: string }> = VEHICLES.map(
  (vehicle) => ({
    id: vehicle.id,
    label: vehicle.label,
  })
);

export type VehicleRequest = "auto" | VehicleClassId;

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
  const alias: Record<string, VehicleRequest> = {
    sedan_suv: "sedan",
    box_16: "box16",
    cargo_van: "cargoVan",
    box_20: "box20",
  };
  const requestedRaw = options?.requested ?? "auto";
  const requested = alias[requestedRaw] ?? requestedRaw;
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
  vehicle: (typeof VEHICLES)[number],
  constructionSite: boolean
): string {
  if (constructionSite && vehicle.id === MerchantVehicleClass.CARGO_VAN) {
    return "Construction site. Cargo van with liftgate will be dispatched. Choose a larger vehicle if you need one.";
  }
  const sedan = vehicleById(MerchantVehicleClass.SEDAN);
  if (vehicle.id !== MerchantVehicleClass.SEDAN && !fits(parcels, sedan)) {
    return `${vehicle.label} will be dispatched. Parcel size or weight does not fit a sedan.`;
  }
  if (!parcels.every(hasCompleteSize)) {
    return `${vehicle.label} will be dispatched. Enter length, width, and height before a sedan can be considered.`;
  }
  return `${vehicle.label} will be dispatched. Quote uses this vehicle, distance, and stops.`;
}

function unfitReason(
  parcels: Parcel[],
  vehicle: (typeof VEHICLES)[number],
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

function fits(parcels: Parcel[], vehicle: (typeof VEHICLES)[number]): boolean {
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

function vehicleById(id: VehicleClassId): (typeof VEHICLES)[number] {
  return VEHICLES.find((vehicle) => vehicle.id === id) ?? VEHICLES[3];
}

function result(input: {
  vehicle: (typeof VEHICLES)[number];
  chargeableWeightKg: number;
  blocked: boolean;
  requestedByMerchant: boolean;
  message: string;
}): VehicleAllocation {
  return {
    band: input.blocked ? FleetBand.OVER_CAPACITY : input.vehicle.band,
    bandLabel: input.vehicle.bandLabel,
    vehicleClass: input.vehicle.id,
    vehicleLabel: input.vehicle.label,
    chargeableWeightKg: input.chargeableWeightKg,
    blocked: input.blocked,
    requestedByMerchant: input.requestedByMerchant,
    message: input.message,
  };
}
