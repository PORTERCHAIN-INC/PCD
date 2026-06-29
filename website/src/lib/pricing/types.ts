import type { Urgency, VehicleClassId } from "@/lib/quote/types";

export type PricingInput = {
  vehicleId: VehicleClassId;
  distanceKm: number;
  durationMinutes: number;
  totalWeightKg: number;
  stopCount?: number;
  needHelper?: boolean;
  urgency?: Urgency;
  trafficMultiplier?: number;
  marginMultiplier?: number;
  /** Canadian postal codes or FSAs for GTA Traffic Engine */
  postalCodes?: string[];
  /** When the shipment runs — defaults to now */
  scheduledAt?: Date | string;
};

export type PricingFeeBreakdown = {
  base_fee: number;
  distance_fee: number;
  time_fee: number;
  weight_fee: number;
  fuel_fee: number;
  stop_fee: number;
  helper_fee: number;
  subtotal: number;
  traffic_multiplier: number;
  margin_multiplier: number;
  adjusted_cost: number;
};

export type PricingResult = {
  customer_price: number;
  driver_payout: number;
  platform_margin: number;
  breakdown: PricingFeeBreakdown;
  currency: "CAD";
};

/** @deprecated Use PricingResult — camelCase bridge for quote engine */
export type PricingResultCamel = {
  customerPrice: number;
  driverPayout: number;
  platformMargin: number;
  breakdown: {
    baseFee: number;
    distanceFee: number;
    timeFee: number;
    weightFee: number;
    fuelFee: number;
    stopFee: number;
    helperFee: number;
    subtotal: number;
    trafficMultiplier: number;
    marginMultiplier: number;
    adjustedCost: number;
  };
  currency: "CAD";
};
