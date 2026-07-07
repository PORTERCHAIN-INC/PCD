import { pricingEngine, toCamelCasePricingResult } from "@/lib/pricing";
import { gtaTrafficEngine, toCamelCaseTrafficResult } from "@/lib/traffic";
import type { TrafficResultCamel } from "@/lib/traffic";
import type { RouteResult, Urgency, VehicleClass } from "./types";
import type { QuoteBreakdown } from "./types";

export type QuotePriceResult = {
  price: number;
  customerPrice: number;
  driverPayout: number;
  platformMargin: number;
  breakdown: QuoteBreakdown;
  traffic: TrafficResultCamel;
};

export function calculateQuotePrice(
  vehicle: VehicleClass,
  route: RouteResult,
  totalWeightKg: number,
  stopCount: number,
  urgency: Urgency,
  needHelper: boolean,
  postalCodes: string[],
  scheduledAt?: string
): QuotePriceResult {
  const at = scheduledAt ?? (urgency === "scheduled" ? undefined : new Date().toISOString());

  const result = pricingEngine.calculate({
    vehicleId: vehicle.id,
    distanceKm: route.distanceKm,
    durationMinutes: route.durationMinutes,
    totalWeightKg,
    stopCount,
    needHelper,
    urgency,
    postalCodes,
    scheduledAt: at,
  });

  const traffic = toCamelCaseTrafficResult(
    gtaTrafficEngine.evaluate({
      postalCodes,
      at: at ?? new Date().toISOString(),
    })
  );

  const camel = toCamelCasePricingResult(result);
  const b = camel.breakdown;

  return {
    price: camel.customerPrice,
    customerPrice: camel.customerPrice,
    driverPayout: camel.driverPayout,
    platformMargin: camel.platformMargin,
    breakdown: {
      baseFee: b.baseFee,
      distanceFee: b.distanceFee,
      timeFee: b.timeFee,
      weightFee: b.weightFee,
      fuelFee: b.fuelFee,
      stopFee: b.stopFee,
      helperFee: b.helperFee,
      trafficMultiplier: b.trafficMultiplier,
      marginMultiplier: b.marginMultiplier,
      subtotal: b.subtotal,
      adjustedCost: b.adjustedCost,
      urgencyMultiplier: b.trafficMultiplier,
    },
    traffic,
  };
}
