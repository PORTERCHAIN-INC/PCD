/**
 * Attribution shape for analytics and backend. Aligned with existing taxonomy
 * (source_page, locale, market) and extended for analytics (sourceSection, landing, UTM).
 */

export type Attribution = {
  sourcePage?: string;
  sourceSection?: string;
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

/**
 * Derive sourcePage from pathname (e.g. /ca/en/industry/coffee-roasters -> industry/coffee-roasters).
 */
function pathnameToSourcePage(pathname: string): string | undefined {
  const segments = pathname.replace(/^\/+|\/+$/g, "").split("/");
  if (segments.length >= 2) {
    const rest = segments.slice(2);
    if (rest.length === 0) return "home";
    return rest.join("/");
  }
  return undefined;
}

/**
 * Capture attribution from the current window (URL, referrer). Call once on client load.
 * Persists to sessionStorage so later events can attach the same landing context.
 */
export function captureAttribution(): Attribution {
  if (typeof window === "undefined") return {};
  try {
    const existing = sessionStorage.getItem(STORAGE_KEY);
    if (existing) {
      return JSON.parse(existing) as Attribution;
    }
    const pathname = window.location.pathname;
    const search = window.location.search;
    const segments = pathname.replace(/^\/+|\/+$/g, "").split("/");
    const market = segments[0];
    const locale = segments[1];
    const attribution: Attribution = {
      sourcePage: pathnameToSourcePage(pathname),
      locale: locale || undefined,
      market: market || undefined,
      landingPageUrl: window.location.href,
      referrer: document.referrer || undefined,
      ...getUtmParams(search),
    };
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(attribution));
    return attribution;
  } catch {
    return {};
  }
}

/**
 * Get stored attribution (from sessionStorage). Call from track() to attach to events.
 */
export function getStoredAttribution(): Attribution {
  if (typeof window === "undefined") return {};
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return captureAttribution();
    return JSON.parse(raw) as Attribution;
  } catch {
    return {};
  }
}

/**
 * Map backend snake_case attribution to our shape (for API payloads we keep snake_case).
 */
export function attributionToBackend(a: Attribution): {
  source_page?: string;
  locale?: string;
  market?: string;
} {
  return {
    ...(a.sourcePage != null && { source_page: a.sourcePage }),
    ...(a.locale != null && { locale: a.locale }),
    ...(a.market != null && { market: a.market }),
  };
}
