import { publicEnv } from "@/lib/env";

/** Unified Porterchain sign-in on the public website (role-based redirect). */
export const unifiedSignInPath = "/login";

/** Retail customer portal on the dedicated app (:3004). */
export const customerPortalDashboardUrl = `${publicEnv.customerPortalUrl}/dashboard`;

/** Legacy embedded customer area on the marketing site. */
export const customerPortalPath = "/portal/customer";
export const customerSignInPath = unifiedSignInPath;

/** Merchant portal sign-in (direct deep-link; prefer unifiedSignInPath from website). */
export const merchantSignInUrl = `${publicEnv.merchantPortalUrl}/sign-in`;

export const merchantPortalUrl = publicEnv.merchantPortalUrl;
export const driverPortalUrl = publicEnv.driverPortalUrl;

export function portalDisplayHost(url: string): string {
  try {
    return new URL(url).host;
  } catch {
    return url.replace(/^https?:\/\//, "").replace(/\/$/, "");
  }
}
