/**
 * DISPLAY-ONLY pricing engine for website UX previews.
 * Authoritative retail pricing is always computed server-side (`services/pricing-engine`).
 * Do not use this output for payment amounts or API `website_pricing` snapshots.
 */
import { getVehicleById } from "@/lib/quote/vehicles";
import { gtaTrafficEngine } from "@/lib/traffic";
import {
  DEFAULT_DRIVER_SHARE,
  DEFAULT_MARGIN_MULTIPLIER,
  HELPER_FEE_CAD,
  TRAFFIC_MULTIPLIERS,
  URGENCY_TRAFFIC_FLOOR,
  VEHICLE_PRICING_RATES,
} from "./rates";
import type { PricingFeeBreakdown, PricingInput, PricingResult, PricingResultCamel } from "./types";

/**
 * Price =
 *   (Base Fee + Distance Fee + Time Fee + Weight Fee + Fuel Fee + stops + helper)
 *   × Traffic Multiplier
 *   × Margin Multiplier  → customer_price
 *
 * driver_payout = adjusted_cost × driver_share
 * platform_margin = customer_price − driver_payout
 */
export class PricingEngine {
  calculate(input: PricingInput): PricingResult {
    const vehicle = getVehicleById(input.vehicleId);
    if (!vehicle) {
      throw new Error(`Unknown vehicle: ${input.vehicleId}`);
    }

    const rates = VEHICLE_PRICING_RATES[input.vehicleId];
    const stopCount = Math.max(0, input.stopCount ?? 0);
    const needHelper = input.needHelper ?? false;
    const urgency = input.urgency ?? "same_day";

    const base_fee = vehicle.baseFeeCad;
    const distance_fee = round2(input.distanceKm * rates.perKmCad);
    const time_fee = round2(input.durationMinutes * rates.perMinuteCad);
    const weight_fee = round2(input.totalWeightKg * rates.perKgCad);
    const fuel_fee = round2(input.distanceKm * rates.fuelPerKmCad);
    const stop_fee = round2(stopCount * rates.perStopCad);
    const helper_fee = needHelper ? HELPER_FEE_CAD : 0;

    const subtotal = round2(
      base_fee + distance_fee + time_fee + weight_fee + fuel_fee + stop_fee + helper_fee
    );

    const traffic_multiplier = resolveTrafficMultiplier(input, urgency);
    const margin_multiplier = input.marginMultiplier ?? DEFAULT_MARGIN_MULTIPLIER;

    const adjusted_cost = round2(subtotal * traffic_multiplier);
    const customer_price = round2(adjusted_cost * margin_multiplier);
    const driver_payout = round2(adjusted_cost * DEFAULT_DRIVER_SHARE);
    const platform_margin = round2(customer_price - driver_payout);

    const breakdown: PricingFeeBreakdown = {
      base_fee,
      distance_fee,
      time_fee,
      weight_fee,
      fuel_fee,
      stop_fee,
      helper_fee,
      subtotal,
      traffic_multiplier,
      margin_multiplier,
      adjusted_cost,
    };

    return {
      customer_price,
      driver_payout,
      platform_margin,
      breakdown,
      currency: "CAD",
    };
  }
}

export const pricingEngine = new PricingEngine();

export function toCamelCasePricingResult(result: PricingResult): PricingResultCamel {
  const b = result.breakdown;
  return {
    customerPrice: result.customer_price,
    driverPayout: result.driver_payout,
    platformMargin: result.platform_margin,
    currency: result.currency,
    breakdown: {
      baseFee: b.base_fee,
      distanceFee: b.distance_fee,
      timeFee: b.time_fee,
      weightFee: b.weight_fee,
      fuelFee: b.fuel_fee,
      stopFee: b.stop_fee,
      helperFee: b.helper_fee,
      subtotal: b.subtotal,
      trafficMultiplier: b.traffic_multiplier,
      marginMultiplier: b.margin_multiplier,
      adjustedCost: b.adjusted_cost,
    },
  };
}

function round2(n: number) {
  return Math.round(n * 100) / 100;
}

function resolveTrafficMultiplier(
  input: PricingInput,
  urgency: NonNullable<PricingInput["urgency"]>
): number {
  if (input.trafficMultiplier != null) {
    return input.trafficMultiplier;
  }

  const urgencyFloor = URGENCY_TRAFFIC_FLOOR[urgency] ?? TRAFFIC_MULTIPLIERS[urgency];

  if (input.postalCodes?.length) {
    const gtaMultiplier = gtaTrafficEngine.getMultiplier({
      postalCodes: input.postalCodes,
      at: input.scheduledAt,
    });
    return Math.max(gtaMultiplier, urgencyFloor);
  }

  return TRAFFIC_MULTIPLIERS[urgency];
}
