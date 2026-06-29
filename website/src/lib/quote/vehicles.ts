import type { VehicleClass } from "./types";

export const VEHICLE_CLASSES: VehicleClass[] = [
  {
    id: "sedan",
    name: "Sedan",
    maxWeightKg: 300,
    maxLengthCm: 120,
    maxWidthCm: 80,
    maxHeightCm: 60,
    maxVolumeM3: 1.2,
    baseFeeCad: 18,
    perKmCad: 1.2,
    perStopCad: 12,
  },
  {
    id: "suv",
    name: "SUV",
    maxWeightKg: 500,
    maxLengthCm: 150,
    maxWidthCm: 100,
    maxHeightCm: 90,
    maxVolumeM3: 2.5,
    baseFeeCad: 22,
    perKmCad: 1.35,
    perStopCad: 14,
  },
  {
    id: "minivan",
    name: "Minivan",
    maxWeightKg: 700,
    maxLengthCm: 180,
    maxWidthCm: 120,
    maxHeightCm: 110,
    maxVolumeM3: 4,
    baseFeeCad: 32,
    perKmCad: 1.5,
    perStopCad: 16,
  },
  {
    id: "cargo_van",
    name: "Cargo Van",
    maxWeightKg: 1200,
    maxLengthCm: 240,
    maxWidthCm: 150,
    maxHeightCm: 140,
    maxVolumeM3: 8,
    baseFeeCad: 42,
    perKmCad: 1.85,
    perStopCad: 18,
  },
  {
    id: "sprinter_van",
    name: "Sprinter",
    maxWeightKg: 1800,
    maxLengthCm: 360,
    maxWidthCm: 180,
    maxHeightCm: 190,
    maxVolumeM3: 14,
    baseFeeCad: 68,
    perKmCad: 2.25,
    perStopCad: 22,
  },
  {
    id: "box_16ft",
    name: "16ft Box Truck",
    maxWeightKg: 3000,
    maxLengthCm: 480,
    maxWidthCm: 210,
    maxHeightCm: 210,
    maxVolumeM3: 22,
    baseFeeCad: 95,
    perKmCad: 2.75,
    perStopCad: 28,
  },
  {
    id: "box_20ft",
    name: "20ft Box Truck",
    maxWeightKg: 4500,
    maxLengthCm: 600,
    maxWidthCm: 240,
    maxHeightCm: 240,
    maxVolumeM3: 30,
    baseFeeCad: 125,
    perKmCad: 3.25,
    perStopCad: 32,
  },
];

export function getVehicleById(id: string): VehicleClass | undefined {
  return VEHICLE_CLASSES.find((v) => v.id === id);
}

/** Vehicle classes available for exclusive whole-vehicle bookings in the home wizard. */
export const WHOLE_VEHICLE_BOOKING_OPTIONS: VehicleClass[] = VEHICLE_CLASSES.filter((v) =>
  ["minivan", "cargo_van", "sprinter_van", "box_16ft", "box_20ft"].includes(v.id)
);

export const WHOLE_VEHICLE_DESCRIPTIONS: Record<string, string> = {
  minivan: "Passenger van — smaller moves & light freight",
  cargo_van: "Full cargo van — pallets, furniture, equipment",
  sprinter_van: "High-roof sprinter — bulky items & long loads",
  box_16ft: "16ft box truck — construction & large freight",
  box_20ft: "20ft box truck — maximum capacity loads",
};
