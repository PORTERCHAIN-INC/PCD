import { isDevelopmentBuild } from "@porterchain/auth/devBypass";

export const publicEnv = {
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
  // Must be the Porterchain Driver instance key (clerk.driver.porterchain.com) — the same Clerk
  // app the driver mobile app uses, so one driver account works on web and mobile.
  clerkPublishableKey: (process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "").trim(),
} as const;

export function isClerkConfigured(): boolean {
  return publicEnv.clerkPublishableKey.length > 0;
}

/**
 * Local dev only: email-only driver login when CLERK_DEV_BYPASS is enabled on the API.
 *
 * Gated on the build, so a shipped portal never offers it (BJ).
 */
export function isDevEmailLogin(): boolean {
  if (!isDevelopmentBuild()) return false;
  if (process.env.NEXT_PUBLIC_DRIVER_DEV_LOGIN === "false") return false;
  if (process.env.NEXT_PUBLIC_DRIVER_DEV_LOGIN === "true") return true;
  const appEnv = (process.env.NEXT_PUBLIC_APP_ENV ?? process.env.NODE_ENV ?? "").trim();
  return appEnv === "local" || appEnv === "development";
}
