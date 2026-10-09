/**
 * First-party visitor intelligence (no fingerprinting).
 * Durable session id + attribution + light journey → quote/CRM handoff.
 */

import { isMobilePhoneBrowser } from "@/lib/device";
import { captureAttribution, getStoredAttribution, type Attribution } from "@/lib/seo/attribution";

export const VISITOR_ID_KEY = "pc_vid";
export const VISITOR_JOURNEY_KEY = "pc_visitor_journey";
export const QUOTE_INTENT_KEY = "pc_quote_intent";

const MAX_PATHS = 24;

export interface VisitorTrackingPayload {
  browser?: string;
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  utm_term?: string;
  utm_content?: string;
  referrer?: string;
  device?: string;
  landing_page?: string;
  from_page?: string;
  locale?: string;
  source_page?: string;
  page_view_count?: number;
  paths?: string[];
  intent?: string;
  guide_stage?: string;
  location?: { city?: string; region?: string; country?: string };
}

export type QuoteIntentHandoff = {
  intent?: string;
  from?: string;
  vehicle?: string;
  /** Merchant referral attribution (`?ref=`). */
  ref?: string;
};

type JourneyState = {
  paths: string[];
  page_view_count: number;
  first_seen_at: string;
  last_seen_at: string;
};

function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `vid-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function readJson<T>(key: string): T | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(key) ?? sessionStorage.getItem(key);
    if (!raw) return null;
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

function writeLocal(key: string, value: string): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(key, value);
  } catch {
    try {
      sessionStorage.setItem(key, value);
    } catch {
      /* private browsing */
    }
  }
}

/** Durable first-party visitor id (localStorage, falls back to sessionStorage). */
export function getOrCreateVisitorId(): string {
  if (typeof window === "undefined") return "";
  try {
    const existing = localStorage.getItem(VISITOR_ID_KEY) ?? sessionStorage.getItem(VISITOR_ID_KEY);
    if (existing?.trim()) return existing.trim().slice(0, 64);
  } catch {
    /* ignore */
  }
  const id = newId().slice(0, 64);
  writeLocal(VISITOR_ID_KEY, id);
  try {
    sessionStorage.setItem(VISITOR_ID_KEY, id);
  } catch {
    /* ignore */
  }
  return id;
}

function loadJourney(): JourneyState {
  const stored = readJson<JourneyState>(VISITOR_JOURNEY_KEY);
  if (stored?.paths && typeof stored.page_view_count === "number") {
    return {
      paths: stored.paths.slice(-MAX_PATHS),
      page_view_count: stored.page_view_count,
      first_seen_at: stored.first_seen_at || new Date().toISOString(),
      last_seen_at: stored.last_seen_at || new Date().toISOString(),
    };
  }
  const now = new Date().toISOString();
  return { paths: [], page_view_count: 0, first_seen_at: now, last_seen_at: now };
}

function saveJourney(journey: JourneyState): void {
  writeLocal(VISITOR_JOURNEY_KEY, JSON.stringify(journey));
}

/** Record a marketing page view (pathname only — no query PII). */
export function recordPageView(pathname?: string): JourneyState {
  if (typeof window === "undefined") {
    return { paths: [], page_view_count: 0, first_seen_at: "", last_seen_at: "" };
  }
  getOrCreateVisitorId();
  captureAttribution();
  const path = (pathname ?? window.location.pathname).slice(0, 256);
  const journey = loadJourney();
  const last = journey.paths[journey.paths.length - 1];
  if (path && path !== last) {
    journey.paths = [...journey.paths, path].slice(-MAX_PATHS);
  }
  journey.page_view_count += 1;
  journey.last_seen_at = new Date().toISOString();
  if (!journey.first_seen_at) journey.first_seen_at = journey.last_seen_at;
  saveJourney(journey);
  return journey;
}

export function rememberQuoteIntent(intent: QuoteIntentHandoff): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(QUOTE_INTENT_KEY, JSON.stringify(intent));
  } catch {
    /* ignore */
  }
}

export function readQuoteIntent(): QuoteIntentHandoff {
  if (typeof window === "undefined") return {};
  try {
    const raw = sessionStorage.getItem(QUOTE_INTENT_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as QuoteIntentHandoff;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function deviceLabel(): string {
  return isMobilePhoneBrowser() ? "mobile" : "desktop";
}

/**
 * Append cross-origin handoff params for customer portal / book redirects.
 * Subdomains do not share localStorage — URL is the bridge.
 */
export function withVisitorHandoff(
  baseUrl: string,
  extra?: Record<string, string | undefined | null>
): string {
  if (typeof window === "undefined") {
    try {
      const u = new URL(baseUrl);
      for (const [k, v] of Object.entries(extra ?? {})) {
        if (v) u.searchParams.set(k, v);
      }
      return u.toString();
    } catch {
      return baseUrl;
    }
  }
  const vid = getOrCreateVisitorId();
  const attr = getStoredAttribution();
  const intent = readQuoteIntent();
  try {
    const u = new URL(baseUrl, window.location.origin);
    u.searchParams.set("pc_vid", vid);
    if (attr.utm_source) u.searchParams.set("utm_source", attr.utm_source);
    if (attr.utm_medium) u.searchParams.set("utm_medium", attr.utm_medium);
    if (attr.utm_campaign) u.searchParams.set("utm_campaign", attr.utm_campaign);
    if (attr.from || intent.from) u.searchParams.set("from", attr.from || intent.from || "");
    if (intent.vehicle) u.searchParams.set("vehicle", intent.vehicle);
    if (intent.intent) u.searchParams.set("intent", intent.intent);
    for (const [k, v] of Object.entries(extra ?? {})) {
      if (v) u.searchParams.set(k, v);
    }
    return u.toString();
  } catch {
    return baseUrl;
  }
}
