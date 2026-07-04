export const mobileEnv = {
  apiBaseUrl: (process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8001").replace(/\/$/, ""),
  googleMapsApiKey: (process.env.EXPO_PUBLIC_GOOGLE_MAPS_API_KEY ?? "").trim(),
  clerkPublishableKey: (process.env.EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "").trim(),
  appKind: "driver" as const,
};

export function isClerkConfigured() {
  return mobileEnv.clerkPublishableKey.length > 0;
}
