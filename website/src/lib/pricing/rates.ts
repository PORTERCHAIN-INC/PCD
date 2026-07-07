import type { VehicleClassId, Urgency } from "@/lib/quote/types";

export type VehiclePricingRates = {
  perKmCad: number;
  perMinuteCad: number;
  perKgCad: number;
  fuelPerKmCad: number;
  perStopCad: number;
};

export const DEFAULT_MARGIN_MULTIPLIER = 1.0;
export const DEFAULT_DRIVER_SHARE = 0.72;

export const TRAFFIC_MULTIPLIERS: Record<Urgency, number> = {
  scheduled: 1.0,
  same_day: 1.0,
  rush: 1.0,
};

/** Minimum traffic multiplier by urgency when GTA traffic engine is active */
export const URGENCY_TRAFFIC_FLOOR: Record<Urgency, number> = {
  scheduled: 1.0,
  same_day: 1.0,
  rush: 1.0,
};

export const HELPER_FEE_CAD = 0;

/** $1.00 / km — display preview only; server pricing is authoritative */
const MIN_RATE: VehiclePricingRates = {
  perKmCad: 1.0,
  perMinuteCad: 0,
  perKgCad: 0,
  fuelPerKmCad: 0,
  perStopCad: 0,
};

/** Per-vehicle rate tiers — base fee lives on VehicleClass.baseFeeCad */
export const VEHICLE_PRICING_RATES: Record<VehicleClassId, VehiclePricingRates> = {
  sedan: MIN_RATE,
  suv: MIN_RATE,
  minivan: MIN_RATE,
  cargo_van: MIN_RATE,
  sprinter_van: MIN_RATE,
  box_16ft: MIN_RATE,
  box_20ft: MIN_RATE,
};
