import { publicEnv } from "@/lib/env";

/**
 * Portal link SSOT for the marketing website.
 *
 * Platform Clerk (retail): website `/login` + `/sign-up` for customer + merchant only.
 * Admin → staff IdP at admin portal. Driver → Driver Clerk at driver portal.
 */

/** Platform Clerk sign-in on the public website (customer / merchant). */
export const unifiedSignInPath = "/login";
/** Platform Clerk open SignUp (customer / merchant). */
export const unifiedSignUpPath = "/sign-up";

/** Retail customer app (:3004) — sole authenticated customer surface. */
export const customerPortalDashboardUrl = `${publicEnv.customerPortalUrl}/dashboard`;
export const customerPortalSignInUrl = `${publicEnv.customerPortalUrl}/sign-in`;

/** Authenticated quote / book surface after Platform sign-up. */
export const customerPortalBookUrl = `${publicEnv.customerPortalUrl}/book`;

/** Marketing “Get a quote” → Clerk sign-up (then customer portal book). */
export function quoteSignUpPath(query?: { from?: string; vehicle?: string }): string {
  const params = new URLSearchParams();
  if (query?.from) params.set("from", query.from);
  if (query?.vehicle) params.set("vehicle", query.vehicle);
  params.set("intent", "quote");
  const q = params.toString();
  return q ? `${unifiedSignUpPath}?${q}` : unifiedSignUpPath;
}

export const merchantSignInUrl = `${publicEnv.merchantPortalUrl}/sign-in`;
/** Admin staff IdP (not Platform Clerk). */
export const adminSignInUrl = `${publicEnv.adminPortalUrl}/sign-in`;
/** Driver Clerk invite-only portal. */
export const driverSignInUrl = `${publicEnv.driverPortalUrl}/login`;

export const merchantPortalUrl = publicEnv.merchantPortalUrl;
export const driverPortalUrl = publicEnv.driverPortalUrl;
export const adminPortalUrl = publicEnv.adminPortalUrl;
/** Admin ops home after Platform login (port 3002). */
export const adminPortalDashboardUrl = `${publicEnv.adminPortalUrl}/dashboard`;

export function portalDisplayHost(url: string): string {
  try {
    return new URL(url).host;
  } catch {
    return url.replace(/^https?:\/\//, "").replace(/\/$/, "");
  }
}
