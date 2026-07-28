import { publicEnv } from "@/lib/env";

/**
 * Portal link SSOT for the marketing website.
 *
 * AUTH LAW (4 isolated Clerk apps — do not implement cross-portal SSO here):
 * - Website `/login` uses the **customer** Clerk app only.
 * - Merchant / admin / driver each have their own Clerk app + host.
 * - Deep-link other roles to their portal sign-in URLs; never claim one password opens all portals.
 * See AUTHENTICATION_ARCHITECTURE.md and infrastructure/deploy/CLERK_APPS_SETUP.md.
 */

/** Customer Clerk sign-in on the public website (portal picker + customer form). */
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

/** Resolve portal sign-in URL from `?intent=` on `/login`. */
export function portalSignInUrlForIntent(intent: string | null | undefined): string | null {
  switch (intent) {
    case "merchant":
      return merchantSignInUrl;
    case "driver":
      return driverSignInUrl;
    case "admin":
    case "staff":
      return adminSignInUrl;
    default:
      return null;
  }
}

export function portalDisplayHost(url: string): string {
  try {
    return new URL(url).host;
  } catch {
    return url.replace(/^https?:\/\//, "").replace(/\/$/, "");
  }
}
