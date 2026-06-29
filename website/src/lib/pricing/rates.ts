import type { VehicleClassId, Urgency } from "@/lib/quote/types";

export type VehiclePricingRates = {
  perKmCad: number;
  perMinuteCad: number;
  perKgCad: number;
  fuelPerKmCad: number;
  perStopCad: number;
};

export const DEFAULT_MARGIN_MULTIPLIER = 1.18;
export const DEFAULT_DRIVER_SHARE = 0.72;

export const TRAFFIC_MULTIPLIERS: Record<Urgency, number> = {
  scheduled: 1.0,
  same_day: 1.15,
  rush: 1.3,
};

/** Minimum traffic multiplier by urgency when GTA traffic engine is active */
export const URGENCY_TRAFFIC_FLOOR: Record<Urgency, number> = {
  scheduled: 1.0,
  same_day: 1.0,
  rush: 1.3,
};

export const HELPER_FEE_CAD = 45;

/** Per-vehicle rate tiers — base fee lives on VehicleClass.baseFeeCad */
export const VEHICLE_PRICING_RATES: Record<VehicleClassId, VehiclePricingRates> = {
  sedan: {
    perKmCad: 1.2,
    perMinuteCad: 0.35,
    perKgCad: 0.02,
    fuelPerKmCad: 0.08,
    perStopCad: 12,
  },
  suv: {
    perKmCad: 1.35,
    perMinuteCad: 0.4,
    perKgCad: 0.025,
    fuelPerKmCad: 0.1,
    perStopCad: 14,
  },
  minivan: {
    perKmCad: 1.5,
    perMinuteCad: 0.45,
    perKgCad: 0.03,
    fuelPerKmCad: 0.12,
    perStopCad: 16,
  },
  cargo_van: {
    perKmCad: 1.85,
    perMinuteCad: 0.55,
    perKgCad: 0.035,
    fuelPerKmCad: 0.15,
    perStopCad: 18,
  },
  sprinter_van: {
    perKmCad: 2.25,
    perMinuteCad: 0.65,
    perKgCad: 0.04,
    fuelPerKmCad: 0.18,
    perStopCad: 22,
  },
  box_16ft: {
    perKmCad: 2.75,
    perMinuteCad: 0.8,
    perKgCad: 0.045,
    fuelPerKmCad: 0.22,
    perStopCad: 28,
  },
  box_20ft: {
    perKmCad: 3.25,
    perMinuteCad: 0.95,
    perKgCad: 0.05,
    fuelPerKmCad: 0.28,
    perStopCad: 32,
  },
};
