/** Admin session helpers. The Keycloak session lives in HttpOnly cookies; the BFF attaches the Bearer. */

/** Sentinel for adminFetch: the BFF attaches the Keycloak access token server-side. */
export const STAFF_COOKIE_TOKEN = "staff_cookie";

/** Sign out of Keycloak (revokes the refresh token, ends the SSO session). */
export async function clearStaffSession(_apiUrl?: string, returnTo = "/sign-in"): Promise<void> {
  if (typeof window !== "undefined") {
    window.location.assign(`/auth/logout?return_to=${encodeURIComponent(returnTo)}`);
  }
}
