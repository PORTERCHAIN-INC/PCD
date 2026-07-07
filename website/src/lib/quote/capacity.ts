import { capacityEngine, toCamelCaseResult } from "@/lib/capacity";
import { quoteItemsToCapacityItems } from "./dimensions";
import type { QuoteItemInput, VehicleClass } from "./types";

export function recommendVehicle(items: QuoteItemInput[]): {
  recommended: VehicleClass | null;
  alternatives: VehicleClass[];
  weightUtilization: number;
  volumeUtilization: number;
  warnings: string[];
} {
  const capacityItems = quoteItemsToCapacityItems(items);
  const result = capacityEngine.evaluate(capacityItems);
  const camel = toCamelCaseResult(result);

  return {
    recommended: camel.recommendedVehicle,
    alternatives: camel.alternativeVehicles,
    weightUtilization: camel.weightUtilization,
    volumeUtilization: camel.volumeUtilization,
    warnings: camel.warnings,
  };
}
