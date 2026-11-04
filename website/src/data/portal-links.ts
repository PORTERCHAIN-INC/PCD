import { publicEnv } from "@/lib/env";

/**
 * Portal link SSOT for the marketing website.
 *
 * Keycloak (retail): website `/login` + `/sign-up` for customer + merchant only.
 * Admin → staff IdP at admin portal. Driver → Keycloak at driver portal.
 */

/** Keycloak sign-in on the public website (customer / merchant). */
export const unifiedSignInPath = "/login";
/** Keycloak open SignUp (customer / merchant). */
export const unifiedSignUpPath = "/sign-up";

/** Retail customer app (:3004) — sole authenticated customer surface. */
export const customerPortalDashboardUrl = `${publicEnv.customerPortalUrl}/dashboard`;

/** Authenticated quote / book surface after Platform sign-up. */
export const customerPortalBookUrl = `${publicEnv.customerPortalUrl}/book`;

/** Marketing “Get a quote” → Keycloak sign-up (then customer portal book). */
export function quoteSignUpPath(query?: { from?: string; vehicle?: string; ref?: string }): string {
  const params = new URLSearchParams();
  if (query?.from) params.set("from", query.from);
  if (query?.vehicle) params.set("vehicle", query.vehicle);
  if (query?.ref) params.set("ref", query.ref);
  params.set("intent", "quote");
  const q = params.toString();
  return q ? `${unifiedSignUpPath}?${q}` : unifiedSignUpPath;
}

/** Admin staff IdP (not Keycloak). */
export const adminSignInUrl = `${publicEnv.adminPortalUrl}/sign-in`;
/** Keycloak invite-only portal. */
export const driverSignInUrl = `${publicEnv.driverPortalUrl}/login`;

export const merchantPortalUrl = publicEnv.merchantPortalUrl;
export const driverPortalUrl = publicEnv.driverPortalUrl;

export function portalDisplayHost(url: string): string {
  try {
    return new URL(url).host;
  } catch {
    return url.replace(/^https?:\/\//, "").replace(/\/$/, "");
  }
}
