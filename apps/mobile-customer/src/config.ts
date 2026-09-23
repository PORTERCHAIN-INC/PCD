import { Platform } from "react-native";

function trimSlash(url: string): string {
  return url.replace(/\/$/, "");
}

export const appEnv = process.env.EXPO_PUBLIC_APP_ENV ?? "development";

export const clerkPublishableKey = (process.env.EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "").trim();

/** Places autocomplete only. Distance and price stay on the API. */
export const googleMapsApiKey = (process.env.EXPO_PUBLIC_GOOGLE_MAPS_API_KEY ?? "").trim();

/** Release and preview builds never skip auth, even if the flag is set. */
export const allowDevAuth = (): boolean => {
  if (!__DEV__) return false;
  if (appEnv === "production" || appEnv === "preview") return false;
  if (process.env.EXPO_PUBLIC_ALLOW_DEV_AUTH === "false") return false;
  return true;
};

export const apiBaseUrl = trimSlash(
  process.env.EXPO_PUBLIC_API_URL ??
    (Platform.OS === "android" ? "http://10.0.2.2:8001" : "http://127.0.0.1:8001")
);

export const fetchTimeoutMs = 12_000;
export const appVersion = "1.0.0";
