import {
  createQuote,
  type CreateQuotePayload,
  type PricingLineItem,
  type QuoteResult,
} from "@/lib/api";
import { buildQuoteRequestFromBooking, type BookingQuoteInput } from "@/lib/quote/booking-mapper";
import type {
  QuoteBreakdown,
  QuoteError,
  QuoteResult as WebsiteQuoteResult,
} from "@/lib/quote/types";

function isWebsiteQuoteError(value: WebsiteQuoteResult | QuoteError): value is QuoteError {
  return "error" in value;
}

function breakdownToLineItems(breakdown: QuoteBreakdown, customerPrice: number): PricingLineItem[] {
  const toCents = (cad: number) => Math.round(cad * 100);
  return [
    { code: "base", label: "Base fee", amount_cents: toCents(breakdown.baseFee) },
    { code: "distance", label: "Distance", amount_cents: toCents(breakdown.distanceFee) },
    { code: "time", label: "Time", amount_cents: toCents(breakdown.timeFee) },
    { code: "weight", label: "Weight", amount_cents: toCents(breakdown.weightFee) },
    { code: "fuel", label: "Fuel surcharge", amount_cents: toCents(breakdown.fuelFee) },
    { code: "stops", label: "Additional stops", amount_cents: toCents(breakdown.stopFee) },
    { code: "helper", label: "Helper", amount_cents: toCents(breakdown.helperFee) },
    {
      code: "traffic",
      label: `Traffic adjustment (×${breakdown.trafficMultiplier.toFixed(2)})`,
      amount_cents: toCents(breakdown.adjustedCost - breakdown.subtotal),
    },
    {
      code: "margin",
      label: `Service fee (×${breakdown.marginMultiplier.toFixed(2)})`,
      amount_cents: toCents(customerPrice - breakdown.adjustedCost),
    },
  ].filter((item) => item.amount_cents !== 0);
}

export type PersistedQuoteResult = QuoteResult & {
  website_quote?: WebsiteQuoteResult;
  pricing_breakdown: PricingLineItem[];
};

export async function computeAndPersistQuote(
  booking: BookingQuoteInput,
  apiPayload: Omit<CreateQuotePayload, "scheduled_at" | "schedule_mode">
): Promise<PersistedQuoteResult> {
  const quoteRequest = buildQuoteRequestFromBooking(booking);

  const response = await fetch("/api/quote", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(quoteRequest),
  });

  const websiteQuote = (await response.json()) as WebsiteQuoteResult | QuoteError;

  if (!response.ok || isWebsiteQuoteError(websiteQuote)) {
    const message =
      "error" in websiteQuote
        ? websiteQuote.error
        : "Could not calculate quote. Please check your addresses.";
    throw new Error(message);
  }

  const scheduledAt = booking.scheduledAt.toISOString();
  const persisted = await createQuote({
    ...apiPayload,
    scheduled_at: scheduledAt,
    schedule_mode: booking.scheduleMode,
    website_pricing: {
      customer_price_cad: websiteQuote.customerPrice,
      driver_payout_cad: websiteQuote.driverPayout,
      platform_margin_cad: websiteQuote.platformMargin,
      distance_km: websiteQuote.route.distanceKm,
      duration_minutes: websiteQuote.route.durationMinutes,
      engine_vehicle_id: websiteQuote.recommendedVehicle.id,
      breakdown: websiteQuote.breakdown,
      traffic: websiteQuote.traffic,
      quote_engine: "website_v1",
    },
  });

  const pricing_breakdown = breakdownToLineItems(
    websiteQuote.breakdown,
    websiteQuote.customerPrice
  );

  return {
    ...persisted,
    pricing_breakdown,
    website_quote: websiteQuote,
  };
}
