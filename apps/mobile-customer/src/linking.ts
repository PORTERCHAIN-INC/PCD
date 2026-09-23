import * as Linking from "expo-linking";

export type VisitorTracking = {
  device?: "ios" | "android";
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  utm_term?: string;
  utm_content?: string;
  from_page?: string;
  intent?: string;
};

export type AppLink = {
  screen: "sign-in" | "track" | "book";
  tracking?: string;
  vehicle?: string;
  quoteId?: string;
  visitorId?: string;
  visitorTracking?: VisitorTracking;
};

function queryString(
  query: Record<string, string | string[] | undefined>,
  key: string
): string | undefined {
  const value = query[key];
  const raw = Array.isArray(value) ? value[0] : value;
  const trimmed = raw?.trim();
  return trimmed ? trimmed : undefined;
}

function visitorTrackingFromQuery(
  query: Record<string, string | string[] | undefined>
): VisitorTracking | undefined {
  const tracking: VisitorTracking = {
    utm_source: queryString(query, "utm_source"),
    utm_medium: queryString(query, "utm_medium"),
    utm_campaign: queryString(query, "utm_campaign"),
    utm_term: queryString(query, "utm_term"),
    utm_content: queryString(query, "utm_content"),
    from_page: queryString(query, "from"),
    intent: queryString(query, "intent"),
  };
  const hasHandoff = Object.entries(tracking).some(([key, value]) => key !== "device" && value);
  return hasHandoff ? tracking : undefined;
}

export function screenFromUrl(url: string | null): AppLink | null {
  if (!url) return null;
  const parsed = Linking.parse(url);
  const path = parsed.path ?? "";
  const query = parsed.queryParams ?? {};
  const vehicle = queryString(query, "vehicle");
  const quoteId = queryString(query, "quote_id");
  const visitorId = queryString(query, "pc_vid")?.slice(0, 64);
  const visitorTracking = visitorTrackingFromQuery(query);
  if (path.includes("track")) {
    const parts = path.split("/").filter(Boolean);
    const idx = parts.findIndex((part) => part === "track");
    const tracking = idx >= 0 ? parts[idx + 1] : undefined;
    return { screen: "track", tracking };
  }
  if (path.includes("book"))
    return { screen: "book", vehicle, quoteId, visitorId, visitorTracking };
  if (path.includes("login") || path.includes("sign-in")) return { screen: "sign-in" };
  return null;
}

/** Inbox deep_link values are paths such as `/track/{n}`. */
export function screenFromDeepLink(deepLink: string | null | undefined): AppLink | null {
  if (!deepLink) return null;
  if (deepLink.startsWith("http")) return screenFromUrl(deepLink);
  return screenFromUrl(`porterchain-customer://${deepLink.replace(/^\//, "")}`);
}
