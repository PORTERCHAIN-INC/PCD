export const publicEnv = {
  porterchainApiUrl: (
    process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ??
    (process.env.NODE_ENV === "development"
      ? "http://localhost:8001"
      : "https://api.porterchain.com")
  ).replace(/\/$/, ""),
  clerkPublishableKey: (process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "").trim(),
  websiteUrl: (
    process.env.NEXT_PUBLIC_WEBSITE_URL ??
    (process.env.NODE_ENV === "development" ? "http://localhost:3000" : "https://porterchain.com")
  ).replace(/\/$/, ""),
} as const;

export function isClerkConfigured(): boolean {
  return publicEnv.clerkPublishableKey.length > 0;
}
