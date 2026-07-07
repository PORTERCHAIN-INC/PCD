import type { NotificationInboxItem } from "./types";

export type ParsedDeepLink = {
  screen?: string;
  params: Record<string, string>;
  raw: string;
};

export function parseDeepLink(deepLink: string, appScheme: string): ParsedDeepLink {
  const raw = deepLink.trim();
  const params: Record<string, string> = {};

  try {
    const normalized = raw.startsWith("http")
      ? new URL(raw)
      : new URL(raw.replace(`${appScheme}://`, "https://app/"));

    const path = normalized.pathname.replace(/^\//, "");
    const segments = path.split("/").filter(Boolean);
    const screen = segments[0];

    normalized.searchParams.forEach((value, key) => {
      params[key] = value;
    });

    if (segments.length > 1 && !params.id) {
      params.id = segments[1];
    }

    return { screen, params, raw };
  } catch {
    return { params, raw };
  }
}

export function deepLinkFromItem(item: NotificationInboxItem, appScheme: string): string | null {
  if (item.deep_link) return item.deep_link;
  if (item.order_id) return `${appScheme}://jobs/${item.order_id}`;
  if (item.ticket_id) return `${appScheme}://support/${item.ticket_id}`;
  if (item.claim_id) return `${appScheme}://claims/${item.claim_id}`;
  return null;
}

export function deepLinkFromPushData(
  data: Record<string, unknown> | undefined,
  appScheme: string
): string | null {
  if (!data) return null;
  const link = data.deep_link ?? data.deepLink;
  if (typeof link === "string" && link.length > 0) return link;
  const orderId = data.order_id ?? data.orderId;
  if (typeof orderId === "string") return `${appScheme}://jobs/${orderId}`;
  return null;
}
