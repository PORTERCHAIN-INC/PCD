export const publicEnv = {
  porterchainApiUrl: (process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ?? "http://localhost:8001").replace(/\/$/, ""),
  clerkPublishableKey: (process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "").trim(),
} as const;

export function isClerkConfigured() {
  return publicEnv.clerkPublishableKey.length > 0;
}
