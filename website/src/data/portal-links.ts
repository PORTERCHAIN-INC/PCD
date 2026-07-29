import { publicEnv } from "@/lib/env";

/**
 * Portal link SSOT for the marketing website.
 *
 * Platform Clerk (single app): website `/login` signs in once, then routes to the
 * provisioned module (admin / merchant / driver / customer) via session-context.
 */

/** Platform Clerk sign-in on the public website. */
export const unifiedSignInPath = "/login";

/** Retail customer app (:3004) — sole authenticated customer surface. */
export const customerPortalDashboardUrl = `${publicEnv.customerPortalUrl}/dashboard`;
export const customerPortalSignInUrl = `${publicEnv.customerPortalUrl}/sign-in`;

/** Legacy book redirects only — marketing CTAs should use `/business` (capacity + pricing). */
export const customerPortalBookUrl = `${publicEnv.customerPortalUrl}/book`;

export const merchantSignInUrl = `${publicEnv.merchantPortalUrl}/sign-in`;
export const adminSignInUrl = `${publicEnv.adminPortalUrl}/sign-in`;
/** Driver portal uses `/login`, not `/sign-in`. */
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
