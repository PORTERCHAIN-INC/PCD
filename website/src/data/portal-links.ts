import { publicEnv } from "@/lib/env";

/** Unified Porterchain sign-in on the public website (role-based redirect). */
export const unifiedSignInPath = "/login";

/** Retail customer app (:3004) — sole authenticated customer surface (masterrule §21). */
export const customerPortalDashboardUrl = `${publicEnv.customerPortalUrl}/dashboard`;
export const customerPortalSignInUrl = `${publicEnv.customerPortalUrl}/sign-in`;
/** Retail booking funnel — sole on-site book surface (masterrule §21 · §1.1.4). */
export const customerPortalBookUrl = `${publicEnv.customerPortalUrl}/book`;

/** @deprecated Use customerPortalDashboardUrl — embedded website portal removed. */
export const customerPortalPath = customerPortalDashboardUrl;
export const customerSignInPath = customerPortalSignInUrl;

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
