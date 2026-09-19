import { BUSINESS_FLEET_KEYS } from "@/data/business";

export type FleetVehicleKey = (typeof BUSINESS_FLEET_KEYS)[number];

export type FleetVehicleSpec = {
  /** Interior cargo height in inches */
  heightIn: number;
  /** Interior cargo width in inches */
  widthIn: number;
  /** Maximum payload in pounds */
  weightLbs: number;
  /** Standard 48×40 in skids; 0 = not applicable */
  skidCapacity: number;
};

/** Cargo-area specs aligned with booking capacity classes and fleet marketing copy. */
export const FLEET_VEHICLE_SPECS: Record<FleetVehicleKey, FleetVehicleSpec> = {
  sedan: { heightIn: 24, widthIn: 36, weightLbs: 50, skidCapacity: 0 },
  suv: { heightIn: 36, widthIn: 42, weightLbs: 150, skidCapacity: 0 },
  pickup: { heightIn: 48, widthIn: 66, weightLbs: 1500, skidCapacity: 0 },
  cargoVan: { heightIn: 55, widthIn: 59, weightLbs: 3000, skidCapacity: 1 },
  highRoof: { heightIn: 75, widthIn: 70, weightLbs: 3500, skidCapacity: 2 },
  box16: { heightIn: 83, widthIn: 83, weightLbs: 6000, skidCapacity: 4 },
  box20: { heightIn: 96, widthIn: 96, weightLbs: 10000, skidCapacity: 6 },
};

export function formatFleetDimension(inches: number): string {
  const feet = Math.floor(inches / 12);
  const remainder = Math.round(inches % 12);
  if (feet <= 0) return `${remainder}"`;
  if (remainder === 0) return `${feet}'`;
  return `${feet}' ${remainder}"`;
}

export function formatFleetWeightLbs(lbs: number): string {
  return `${lbs.toLocaleString("en-CA")} lb`;
}
