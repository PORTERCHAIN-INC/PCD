/**
 * Privacy-respecting conversion events: only sent when the visitor has granted
 * the analytics category in the cookie banner (PIPEDA / GDPR). Nothing is
 * queued or sent otherwise — no ad pixels, no server-side conversion APIs.
 */

import { readStoredConsent } from "@/lib/marketing/consent";
import { track, type AnalyticsEventProperties } from "@/lib/seo/analytics";

export const CONVERSION_EVENTS = {
  DELIVERY_CTA_CLICK: "delivery_cta_click",
  CALCULATOR_ESTIMATE: "calculator_estimate",
  CALCULATOR_LEAD: "calculator_lead_submitted",
  HERO_EXPOSURE: "hero_experiment_exposure",
} as const;

export function trackConversion(event: string, properties: AnalyticsEventProperties = {}): boolean {
  if (typeof window === "undefined") return false;
  const consent = readStoredConsent();
  if (!consent?.analytics) return false;
  track(event, properties);
  return true;
}
