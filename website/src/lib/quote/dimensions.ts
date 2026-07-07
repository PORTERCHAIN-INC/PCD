import type { QuoteItemInput, ItemTotals } from "./types";
import {
  calculateVolumeM3,
  calculateCargoTotals,
  capacityEngine,
  type CapacityItem,
} from "@/lib/capacity";

const INCHES_TO_CM = 2.54;

export function inchesToCm(inches: number): number {
  return inches * INCHES_TO_CM;
}

export function quoteItemsToCapacityItems(items: QuoteItemInput[]): CapacityItem[] {
  return items.map((item) => ({
    weightKg: item.weight,
    lengthCm: inchesToCm(item.length),
    widthCm: inchesToCm(item.width),
    heightCm: inchesToCm(item.height),
    quantity: Math.max(1, item.quantity || 1),
  }));
}

export function calculateItemTotals(items: QuoteItemInput[]): ItemTotals {
  const capacityItems = quoteItemsToCapacityItems(items);
  const cargo = calculateCargoTotals(capacityItems);

  let maxLengthCm = 0;
  let maxWidthCm = 0;
  let maxHeightCm = 0;
  let totalQuantity = 0;

  for (const item of capacityItems) {
    maxLengthCm = Math.max(maxLengthCm, item.lengthCm);
    maxWidthCm = Math.max(maxWidthCm, item.widthCm);
    maxHeightCm = Math.max(maxHeightCm, item.heightCm);
    totalQuantity += item.quantity;
  }

  return {
    totalWeightKg: cargo.totalWeightKg,
    totalVolumeM3: cargo.totalVolumeM3,
    maxLengthCm: round2(maxLengthCm),
    maxWidthCm: round2(maxWidthCm),
    maxHeightCm: round2(maxHeightCm),
    totalQuantity,
  };
}

export { calculateVolumeM3 };

function round2(n: number) {
  return Math.round(n * 100) / 100;
}
