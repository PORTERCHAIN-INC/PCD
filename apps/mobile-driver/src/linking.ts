import * as Linking from "expo-linking";

export type DriverLink =
  { kind: "invite"; token: string } | { kind: "job"; orderId: string } | { kind: "none" };

function pathOf(url: string): string {
  const parsed = Linking.parse(url);
  const path = (parsed.path ?? "").replace(/^\//, "");
  return path;
}

export function parseInviteUrl(url: string | null): string | null {
  const link = parseDriverLink(url);
  return link.kind === "invite" ? link.token : null;
}

export function parseJobUrl(url: string | null): string | null {
  const link = parseDriverLink(url);
  return link.kind === "job" ? link.orderId : null;
}

export function parseDriverLink(url: string | null): DriverLink {
  if (!url) return { kind: "none" };

  // Custom scheme: porterchain-driver://jobs/<id>
  const custom = url.match(/(?:porterchain-driver:\/\/|porterchain-driver:\/)jobs\/([^/?#]+)/i);
  if (custom?.[1]) {
    return { kind: "job", orderId: decodeURIComponent(custom[1]) };
  }

  const parsed = Linking.parse(url);
  const path = pathOf(url);
  const q = parsed.queryParams ?? {};

  if (path.includes("driver-invite")) {
    const token = q.token;
    if (typeof token === "string" && token) return { kind: "invite", token };
  }

  // /jobs/<orderId> or jobs/<orderId>
  const jobs = path.match(/(?:^|\/)jobs\/([^/]+)\/?$/i);
  if (jobs?.[1]) {
    return { kind: "job", orderId: decodeURIComponent(jobs[1]) };
  }

  const orderId = q.order_id ?? q.orderId;
  if (typeof orderId === "string" && orderId) {
    return { kind: "job", orderId };
  }

  return { kind: "none" };
}

export function orderIdFromPushData(
  data: Record<string, unknown> | undefined | null
): string | null {
  if (!data) return null;
  const direct = data.order_id ?? data.orderId;
  if (typeof direct === "string" && direct) return direct;
  const link = data.driver_deep_link ?? data.deep_link ?? data.url;
  if (typeof link === "string") {
    const parsed =
      parseJobUrl(link) ??
      parseJobUrl(`https://driver.porterchain.com${link.startsWith("/") ? link : `/${link}`}`);
    if (parsed) return parsed;
  }
  return null;
}
