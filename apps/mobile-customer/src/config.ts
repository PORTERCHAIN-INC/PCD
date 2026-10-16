import { Platform } from "react-native";

function trimSlash(url: string): string {
  return url.replace(/\/$/, "");
}

export const appEnv = process.env.EXPO_PUBLIC_APP_ENV ?? "development";

export const clerkPublishableKey = (process.env.EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "").trim();

/** Release and preview builds never skip auth, even if the flag is set. */
export const allowDevAuth = (): boolean => {
  if (!__DEV__) return false;
  if (appEnv === "production" || appEnv === "preview") return false;
  if (process.env.EXPO_PUBLIC_ALLOW_DEV_AUTH === "false") return false;
  return true;
};

const PROD_API = "https://api.porterchain.com";
const isLocal = (u: string) =>
  /\/\/(localhost|127\.0\.0\.1|10\.0\.2\.2|0\.0\.0\.0)(:|\/|$)/i.test(u);

/**
 * Release builds can never point at a developer machine: a missing or local
 * EXPO_PUBLIC_API_URL falls back to production instead of localhost.
 */
export function resolveApiBaseUrl(
  envUrl: string | undefined,
  dev: boolean,
  os: string = Platform.OS
): string {
  const url = (envUrl ?? "").trim();
  if (dev) {
    return trimSlash(url || (os === "android" ? "http://10.0.2.2:8001" : "http://127.0.0.1:8001"));
  }
  return trimSlash(url && !isLocal(url) ? url : PROD_API);
}

export const apiBaseUrl = resolveApiBaseUrl(
  process.env.EXPO_PUBLIC_API_URL,
  __DEV__ && appEnv !== "production" && appEnv !== "preview"
);

/** Public website: the one tracking page (map, photo, rating, receipt, cancel, report a problem). */
export const websiteUrl = (() => {
  const u = trimSlash((process.env.EXPO_PUBLIC_WEBSITE_URL ?? "").trim());
  return u && (__DEV__ || !isLocal(u)) ? u : "https://porterchain.com";
})();

/** Customer web portal: documents are attached there (file picking + secure upload). */
export const customerPortalUrl = trimSlash(
  (process.env.EXPO_PUBLIC_CUSTOMER_PORTAL_URL ?? "https://customer.porterchain.com").trim()
);
export const fetchTimeoutMs = 12_000;
export const appVersion = "1.0.0";
