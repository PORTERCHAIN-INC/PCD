/**
 * Privacy-respecting conversion events: only sent when the visitor has granted
 * the analytics category in the cookie banner (PIPEDA / GDPR). Nothing is
 * queued or sent otherwise — no ad pixels, no server-side conversion APIs.
 */

import { readStoredConsent } from "@/lib/marketing/consent";
import { track, type AnalyticsEventProperties } from "@/lib/seo/analytics";

/**
 * Funnel for the weekly review (GA4 → Explore → Funnel): price_requested → calculator_estimate
 * (or price_out_of_area) → book_started. Mark calculator_estimate and book_started as key events.
 */
export const CONVERSION_EVENTS = {
  DELIVERY_CTA_CLICK: "delivery_cta_click",
  /** Visitor submitted two postal codes + a vehicle. */
  PRICE_REQUESTED: "price_requested",
  /** A price was shown. */
  CALCULATOR_ESTIMATE: "calculator_estimate",
  /** Pickup or drop-off is outside the 150 km coverage (demand signal for new areas). */
  PRICE_OUT_OF_AREA: "price_out_of_area",
  /** Clicked "Book" on a priced trip (hand-off to /book). */
  BOOK_STARTED: "book_started",
  CALCULATOR_LEAD: "calculator_lead_submitted",
  /** Shopify app CTA (app is in review; tracks merchant interest). */
  SHOPIFY_CTA_CLICK: "shopify_cta_click",
  HERO_EXPOSURE: "hero_experiment_exposure",
} as const;

export const OUT_OF_AREA_ERRORS: ReadonlySet<string> = new Set([
  "pickup_outside_service_area",
  "dropoff_outside_service_area",
]);

export function trackConversion(event: string, properties: AnalyticsEventProperties = {}): boolean {
  if (typeof window === "undefined") return false;
  const consent = readStoredConsent();
  if (!consent?.analytics) return false;
  track(event, properties);
  return true;
}
