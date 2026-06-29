import { VEHICLE_CLASSES } from "@/lib/quote/vehicles";
import type { VehicleClass } from "@/lib/quote/types";
import type { CapacityCargo, CapacityItem, CapacityResult, CapacityResultCamel } from "./types";

const CM3_PER_M3 = 1_000_000;

/**
 * volume_m3 = (length_cm × width_cm × height_cm × quantity) / 1_000_000
 */
export function calculateVolumeM3(
  lengthCm: number,
  widthCm: number,
  heightCm: number,
  quantity: number
): number {
  return (lengthCm * widthCm * heightCm * quantity) / CM3_PER_M3;
}

export function calculateCargoTotals(items: CapacityItem[]): CapacityCargo {
  let totalWeightKg = 0;
  let totalVolumeM3 = 0;

  for (const item of items) {
    const qty = Math.max(1, item.quantity || 1);
    totalWeightKg += item.weightKg * qty;
    totalVolumeM3 += calculateVolumeM3(item.lengthCm, item.widthCm, item.heightCm, qty);
  }

  return {
    totalWeightKg: round4(totalWeightKg),
    totalVolumeM3: round6(totalVolumeM3),
  };
}

export function vehicleFitsCargo(cargo: CapacityCargo, vehicle: VehicleClass): boolean {
  return cargo.totalWeightKg <= vehicle.maxWeightKg && cargo.totalVolumeM3 <= vehicle.maxVolumeM3;
}

export function selectSmallestVehicle(
  cargo: CapacityCargo,
  vehicles: VehicleClass[] = VEHICLE_CLASSES
): VehicleClass | null {
  return vehicles.find((vehicle) => vehicleFitsCargo(cargo, vehicle)) ?? null;
}

export function calculateUtilization(
  cargo: CapacityCargo,
  vehicle: VehicleClass
): { weight_utilization: number; volume_utilization: number } {
  return {
    weight_utilization: round4(cargo.totalWeightKg / vehicle.maxWeightKg),
    volume_utilization: round4(cargo.totalVolumeM3 / vehicle.maxVolumeM3),
  };
}

export class CapacityEngine {
  evaluate(items: CapacityItem[]): CapacityResult {
    const cargo = calculateCargoTotals(items);
    const recommended_vehicle = selectSmallestVehicle(cargo);
    const warnings: string[] = [];

    if (!recommended_vehicle) {
      warnings.push(
        "Cargo exceeds all supported vehicle classes. Contact operations for LTL or specialized freight."
      );
      return {
        recommended_vehicle: null,
        weight_utilization: 0,
        volume_utilization: 0,
        cargo,
        alternative_vehicles: [],
        warnings,
      };
    }

    const { weight_utilization, volume_utilization } = calculateUtilization(
      cargo,
      recommended_vehicle
    );

    const fitting = VEHICLE_CLASSES.filter((v) => vehicleFitsCargo(cargo, v));
    const alternative_vehicles = fitting.filter((v) => v.id !== recommended_vehicle.id).slice(0, 2);

    if (recommended_vehicle.id === "box_20ft") {
      warnings.push("Large freight — confirm dock access and liftgate requirements at delivery.");
    }

    if (weight_utilization > 0.9) {
      warnings.push("Weight utilization above 90% — confirm declared weight is accurate.");
    }

    if (volume_utilization > 0.9) {
      warnings.push("Volume utilization above 90% — confirm cargo dimensions are accurate.");
    }

    return {
      recommended_vehicle,
      weight_utilization,
      volume_utilization,
      cargo,
      alternative_vehicles,
      warnings,
    };
  }
}

export const capacityEngine = new CapacityEngine();

export function toCamelCaseResult(result: CapacityResult): CapacityResultCamel {
  return {
    recommendedVehicle: result.recommended_vehicle,
    weightUtilization: result.weight_utilization,
    volumeUtilization: result.volume_utilization,
    cargo: result.cargo,
    alternativeVehicles: result.alternative_vehicles,
    warnings: result.warnings,
  };
}

function round4(n: number) {
  return Math.round(n * 10000) / 10000;
}

function round6(n: number) {
  return Math.round(n * 1000000) / 1000000;
}
