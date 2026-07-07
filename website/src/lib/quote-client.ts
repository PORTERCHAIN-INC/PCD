import {
  createQuote,
  type CreateQuotePayload,
  type PricingLineItem,
  type QuoteResult,
} from "@/lib/api";
import { buildQuoteRequestFromBooking, type BookingQuoteInput } from "@/lib/quote/booking-mapper";
import type { QuoteError, QuoteResult as WebsiteQuoteResult } from "@/lib/quote/types";

function isWebsiteQuoteError(value: WebsiteQuoteResult | QuoteError): value is QuoteError {
  return "error" in value;
}

export type PersistedQuoteResult = QuoteResult & {
  /** Non-authoritative client preview — server `amount_cents` is the source of truth. */
  website_quote?: WebsiteQuoteResult;
  pricing_breakdown: PricingLineItem[];
};

/**
 * Persist a quote via Porterchain API. Server-side `porterchain_pricing` owns amount_cents.
 * Optional `/api/quote` call is display-only for instant UX feedback.
 */
export async function computeAndPersistQuote(
  booking: BookingQuoteInput,
  apiPayload: Omit<CreateQuotePayload, "scheduled_at" | "schedule_mode">
): Promise<PersistedQuoteResult> {
  const scheduledAt = booking.scheduledAt.toISOString();

  let websiteQuote: WebsiteQuoteResult | undefined;
  try {
    const quoteRequest = buildQuoteRequestFromBooking(booking);
    const response = await fetch("/api/quote", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(quoteRequest),
    });
    const preview = (await response.json()) as WebsiteQuoteResult | QuoteError;
    if (response.ok && !isWebsiteQuoteError(preview)) {
      websiteQuote = preview;
    }
  } catch {
    // Display preview is optional — server quote is authoritative.
  }

  const persisted = await createQuote({
    ...apiPayload,
    scheduled_at: scheduledAt,
    schedule_mode: booking.scheduleMode,
  });

  const pricing_breakdown =
    persisted.pricing_breakdown ??
    (websiteQuote
      ? [
          {
            code: "total",
            label: "Estimated total (preview)",
            amount_cents: Math.round(websiteQuote.customerPrice * 100),
          },
        ]
      : []);

  return {
    ...persisted,
    pricing_breakdown,
    website_quote: websiteQuote,
  };
}
