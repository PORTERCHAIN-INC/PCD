import { Platform } from "react-native";

function trimSlash(url: string): string {
  return url.replace(/\/$/, "");
}

export const appEnv = process.env.EXPO_PUBLIC_APP_ENV ?? "development";

export const clerkPublishableKey = (process.env.EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "").trim();

/** Release, preview, and store builds never skip Clerk, even if the flag is set. */
export const isStoreProfile = appEnv === "production" || appEnv === "preview";

export const allowDevAuth = (): boolean => {
  if (!__DEV__ || isStoreProfile) return false;
  if (process.env.EXPO_PUBLIC_ALLOW_DEV_AUTH === "false") return false;
  return true;
};

export const apiBaseUrl = trimSlash(
  process.env.EXPO_PUBLIC_API_URL ??
    (Platform.OS === "android" ? "http://10.0.2.2:8001" : "http://127.0.0.1:8001")
);

export const fetchTimeoutMs = 12_000;
export const locationPingMs = 25_000;

/** Dispatch contact. Overridden by the server's support hub (ops_hotline / ops_email) when it answers. */
export const dispatchPhone = (process.env.EXPO_PUBLIC_DISPATCH_PHONE ?? "").trim();
export const dispatchEmail = (
  process.env.EXPO_PUBLIC_DISPATCH_EMAIL ?? "support@porterchain.com"
).trim();

/** Earnings, documents, onboarding, inbox history live on the driver web portal. */
export const driverPortalUrl = (
  process.env.EXPO_PUBLIC_DRIVER_PORTAL_URL ?? "https://driver.porterchain.com"
).replace(/\/$/, "");

/**
 * Days PorterChain keeps on-duty GPS points. Shown to the driver on the consent screen, so it
 * MUST match the server retention job and the privacy policy before a store release.
 */
export const locationRetentionDays = Number(process.env.EXPO_PUBLIC_LOCATION_RETENTION_DAYS ?? 30);
