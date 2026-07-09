/**
 * Attribution shape for analytics and backend. Aligned with existing taxonomy
 * (source_page, locale, market) and extended for analytics (sourceSection, landing, UTM).
 */

export type Attribution = {
  sourcePage?: string;
  sourceSection?: string;
  /** Last-touch `from=` query param (Lane B bridge, pricing, trust, etc.). */
  from?: string;
  locale?: string;
  market?: string;
  landingPageUrl?: string;
  referrer?: string;
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  utm_term?: string;
  utm_content?: string;
};

const STORAGE_KEY = "porterchain_attribution";

function getUtmParams(
  search: string
): Partial<
  Pick<Attribution, "utm_source" | "utm_medium" | "utm_campaign" | "utm_term" | "utm_content">
> {
  const params = new URLSearchParams(search);
  const out: Partial<Attribution> = {};
  const keys = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"] as const;
  keys.forEach((k) => {
    const v = params.get(k);
    if (v) out[k] = v;
  });
  return out;
}

function isLocaleSegment(segment: string): boolean {
  return segment === "en" || segment === "fr";
}

/**
 * Derive sourcePage from pathname (e.g. /en/industry/coffee-roasters → industry/coffee-roasters).
 */
function pathnameToSourcePage(pathname: string): string | undefined {
  const segments = pathname
    .replace(/^\/+|\/+$/g, "")
    .split("/")
    .filter(Boolean);
  if (segments.length === 0) return "home";
  if (segments.length === 1 && isLocaleSegment(segments[0]!)) return "home";
  if (segments.length >= 2 && isLocaleSegment(segments[0]!)) {
    return segments.slice(1).join("/") || "home";
  }
  return segments.join("/");
}

function readStoredAttribution(): Attribution | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as Attribution;
  } catch {
    return null;
  }
}

function writeAttribution(attribution: Attribution): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(attribution));
  } catch {
    /* private browsing */
  }
}

/**
 * Capture attribution from the current window (URL, referrer). Call on client navigation.
 * Persists to sessionStorage; `from=` and UTM params use last-touch overlay on each visit.
 */
export function captureAttribution(): Attribution {
  if (typeof window === "undefined") return {};

  const pathname = window.location.pathname;
  const search = window.location.search;
  const segments = pathname
    .replace(/^\/+|\/+$/g, "")
    .split("/")
    .filter(Boolean);
  const locale = segments[0] && isLocaleSegment(segments[0]) ? segments[0] : undefined;
  const fromParam = new URLSearchParams(search).get("from") ?? undefined;

  const existing = readStoredAttribution();
  const base: Attribution = existing ?? {
    sourcePage: pathnameToSourcePage(pathname),
    locale,
    landingPageUrl: window.location.href,
    referrer: document.referrer || undefined,
    ...getUtmParams(search),
  };

  const merged: Attribution = {
    ...base,
    ...getUtmParams(search),
    ...(fromParam ? { from: fromParam } : {}),
    sourcePage: pathnameToSourcePage(pathname) ?? base.sourcePage,
    locale: locale ?? base.locale,
  };

  if (!existing?.landingPageUrl) {
    merged.landingPageUrl = window.location.href;
    merged.referrer = document.referrer || undefined;
  }

  writeAttribution(merged);
  return merged;
}

/**
 * Get stored attribution (from sessionStorage). Call from track() to attach to events.
 */
export function getStoredAttribution(): Attribution {
  if (typeof window === "undefined") return {};
  const stored = readStoredAttribution();
  if (stored) return stored;
  return captureAttribution();
}

/**
 * Resolved lead source for CRM / mailto (explicit `from=` wins, then path, then landing).
 */
export function resolveLeadSource(explicitFrom?: string): string | undefined {
  const att = getStoredAttribution();
  return explicitFrom ?? att.from ?? att.sourcePage;
}

/**
 * Map backend snake_case attribution to our shape (for API payloads we keep snake_case).
 */
export function attributionToBackend(a: Attribution): {
  source_page?: string;
  from?: string;
  locale?: string;
  market?: string;
} {
  return {
    ...(a.sourcePage != null && { source_page: a.sourcePage }),
    ...(a.from != null && { from: a.from }),
    ...(a.locale != null && { locale: a.locale }),
    ...(a.market != null && { market: a.market }),
  };
}
