import { clerkDevBypassEnabled } from "@porterchain/auth/devBypass";

function resolveApiUrl() {
  const raw = process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL?.trim();
  if (raw) return raw.replace(/\/$/, "");
  return process.env.NODE_ENV === "development"
    ? "http://localhost:8001"
    : "https://api.porterchain.com";
}

export const publicEnv = {
  porterchainApiUrl: resolveApiUrl(),
  websiteUrl: (
    process.env.NEXT_PUBLIC_WEBSITE_URL ??
    (process.env.NODE_ENV === "development" ? "http://localhost:3000" : "https://porterchain.com")
  ).replace(/\/$/, ""),
  clerkPublishableKey: (process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "").trim(),
  googleMapsApiKey: (
    process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY ??
    process.env.GOOGLE_MAPS_BROWSER_API_KEY ??
    ""
  ).trim(),
  appEnv: (process.env.NEXT_PUBLIC_APP_ENV ?? process.env.NODE_ENV ?? "production").trim(),
} as const;

export function isLocalDev() {
  return publicEnv.appEnv === "local" || publicEnv.appEnv === "development";
}

/**
 * When true, Local Super Admin CTA is shown on staff sign-in.
 * API must also have CLERK_DEV_BYPASS=true (development project mode).
 *
 * Gated on the build, so a production bundle always returns false (BJ).
 * The CTA mints a real Staff IdP session — it does not send Bearer ``dev``.
 */
export function useClerkDevApiBypass() {
  return clerkDevBypassEnabled();
}

export function isClerkConfigured() {
  return publicEnv.clerkPublishableKey.length > 0;
}

export function isGoogleMapsConfigured() {
  return publicEnv.googleMapsApiKey.length > 0;
}
