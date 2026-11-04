import { authDevBypassEnabled } from "@porterchain/auth/devBypass";

export const publicEnv = {
  siteUrl: (
    process.env.NEXT_PUBLIC_SITE_URL ??
    (process.env.NODE_ENV === "development"
      ? "http://localhost:3001"
      : "https://merchant.porterchain.com")
  ).replace(/\/$/, ""),
  porterchainApiUrl: (
    process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ??
    (process.env.NODE_ENV === "development"
      ? "http://localhost:8001"
      : "https://api.porterchain.com")
  ).replace(/\/$/, ""),
  websiteUrl: (
    process.env.NEXT_PUBLIC_WEBSITE_URL ??
    (process.env.NODE_ENV === "development" ? "http://localhost:3000" : "https://porterchain.com")
  ).replace(/\/$/, ""),
  keycloakClientId: (process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID ?? "").trim(),
} as const;

export function isAuthConfigured(): boolean {
  return publicEnv.keycloakClientId.length > 0;
}

/**
 * Local only: Bearer `dev` when the API has IDP_DEV_BYPASS=true.
 *
 * Gated on the build, not just the variable — a production bundle always returns
 * false even if the variable leaks into the deploy (BJ).
 */
export function useIdpDevApiBypass(): boolean {
  return authDevBypassEnabled();
}

/** Local portals skip the Keycloak sign-in widget and use the API bypass session. */
export function useLocalDevAuth(): boolean {
  return useIdpDevApiBypass();
}
