/** Client-side visitor tracking metadata for anonymous quote flow. */

import { isMobilePhoneBrowser } from "@/lib/device";

export interface VisitorTrackingPayload {
  browser?: string;
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  referrer?: string;
  device?: string;
  location?: { city?: string; region?: string; country?: string };
}

function getUtm(param: string): string | undefined {
  if (typeof window === "undefined") return undefined;
  return new URLSearchParams(window.location.search).get(param) ?? undefined;
}

export function getVisitorTracking(): VisitorTrackingPayload {
  if (typeof window === "undefined") return {};
  const ua = navigator.userAgent;
  return {
    browser: ua.slice(0, 120),
    utm_source: getUtm("utm_source"),
    utm_medium: getUtm("utm_medium"),
    utm_campaign: getUtm("utm_campaign"),
    referrer: document.referrer || undefined,
    device: isMobilePhoneBrowser() ? "mobile" : "desktop",
  };
}
