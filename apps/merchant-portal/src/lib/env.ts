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
  clerkPublishableKey: (process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "").trim(),
  googleMapsApiKey: (
    process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY ??
    process.env.GOOGLE_MAPS_BROWSER_API_KEY ??
    ""
  ).trim(),
} as const;

export function isGoogleMapsConfigured(): boolean {
  return publicEnv.googleMapsApiKey.length > 0;
}

export function isClerkConfigured(): boolean {
  return publicEnv.clerkPublishableKey.length > 0;
}

/** Local only: Bearer `dev` when API has CLERK_DEV_BYPASS=true. Never use in production builds. */
export function useClerkDevApiBypass(): boolean {
  return process.env.NEXT_PUBLIC_CLERK_DEV_BYPASS === "true";
}
