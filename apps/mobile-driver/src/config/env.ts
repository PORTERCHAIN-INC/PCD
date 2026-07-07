import Constants from "expo-constants";

const extra = (Constants.expoConfig?.extra ?? {}) as {
  apiUrl?: string;
  clerkPublishableKey?: string;
  appKind?: string;
};

export const mobileEnv = {
  apiBaseUrl: (process.env.EXPO_PUBLIC_API_URL ?? extra.apiUrl ?? "http://localhost:8001").replace(
    /\/$/,
    ""
  ),
  googleMapsApiKey: (process.env.EXPO_PUBLIC_GOOGLE_MAPS_API_KEY ?? "").trim(),
  clerkPublishableKey: (
    process.env.EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY ??
    extra.clerkPublishableKey ??
    ""
  ).trim(),
  appKind: "driver" as const,
};

export function isClerkConfigured() {
  return mobileEnv.clerkPublishableKey.length > 0;
}
