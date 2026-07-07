import type { VehicleClass } from "@/lib/quote/types";

export type CapacityItem = {
  weightKg: number;
  lengthCm: number;
  widthCm: number;
  heightCm: number;
  quantity: number;
};

export type CapacityCargo = {
  totalWeightKg: number;
  totalVolumeM3: number;
};

export type CapacityResult = {
  recommended_vehicle: VehicleClass | null;
  weight_utilization: number;
  volume_utilization: number;
  cargo: CapacityCargo;
  alternative_vehicles: VehicleClass[];
  warnings: string[];
};

/** @deprecated Use CapacityResult — kept for quote engine camelCase bridge */
export type CapacityResultCamel = {
  recommendedVehicle: VehicleClass | null;
  weightUtilization: number;
  volumeUtilization: number;
  cargo: CapacityCargo;
  alternativeVehicles: VehicleClass[];
  warnings: string[];
};
