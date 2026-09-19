/**
 * Cross-origin visitor handoff from marketing site → customer portal.
 * Reads `pc_vid` + UTM from URL once, then persists in sessionStorage.
 */

export const VISITOR_ID_KEY = "pc_vid";
export const VISITOR_TRACKING_KEY = "pc_visitor_tracking";

export type VisitorTrackingPayload = {
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
};

function isMobile(): boolean {
  if (typeof navigator === "undefined") return false;
  return /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent);
}

/** Capture handoff query params into sessionStorage (idempotent). */
export function captureVisitorHandoff(searchParams: URLSearchParams): string | null {
  if (typeof window === "undefined") return null;
  const vid = (searchParams.get("pc_vid") || "").trim().slice(0, 64);
  if (vid) {
    try {
      sessionStorage.setItem(VISITOR_ID_KEY, vid);
    } catch {
      /* ignore */
    }
  }

  const tracking: VisitorTrackingPayload = {
    utm_source: searchParams.get("utm_source") || undefined,
    utm_medium: searchParams.get("utm_medium") || undefined,
    utm_campaign: searchParams.get("utm_campaign") || undefined,
    utm_term: searchParams.get("utm_term") || undefined,
    utm_content: searchParams.get("utm_content") || undefined,
    from_page: searchParams.get("from") || undefined,
    intent: searchParams.get("intent") || undefined,
    referrer: typeof document !== "undefined" ? document.referrer || undefined : undefined,
    browser: typeof navigator !== "undefined" ? navigator.userAgent.slice(0, 120) : undefined,
    device: isMobile() ? "mobile" : "desktop",
  };

  const hasSignal = Object.values(tracking).some((v) => v != null && v !== "");
  if (hasSignal) {
    try {
      const prev = readStoredTracking();
      sessionStorage.setItem(VISITOR_TRACKING_KEY, JSON.stringify({ ...prev, ...tracking }));
    } catch {
      /* ignore */
    }
  }

  return getVisitorSessionId();
}

export function getVisitorSessionId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const id = sessionStorage.getItem(VISITOR_ID_KEY)?.trim();
    return id ? id.slice(0, 64) : null;
  } catch {
    return null;
  }
}

function readStoredTracking(): VisitorTrackingPayload {
  try {
    const raw = sessionStorage.getItem(VISITOR_TRACKING_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as VisitorTrackingPayload;
  } catch {
    return {};
  }
}

export function getVisitorTrackingPayload(): VisitorTrackingPayload {
  if (typeof window === "undefined") return {};
  const stored = readStoredTracking();
  return {
    browser: stored.browser ?? navigator.userAgent.slice(0, 120),
    device: stored.device ?? (isMobile() ? "mobile" : "desktop"),
    referrer: stored.referrer ?? (document.referrer || undefined),
    utm_source: stored.utm_source,
    utm_medium: stored.utm_medium,
    utm_campaign: stored.utm_campaign,
    utm_term: stored.utm_term,
    utm_content: stored.utm_content,
    from_page: stored.from_page,
    intent: stored.intent,
    landing_page: stored.landing_page,
    locale: stored.locale,
    source_page: stored.source_page,
    page_view_count: stored.page_view_count,
    paths: stored.paths,
  };
}
