import type { SecurityPolicy } from "./types";

export const DEFAULT_SECURITY_POLICY: SecurityPolicy = {
  sessionTimeoutMinutes: 15,
  pinLength: 6,
  enableIntegrityCheck: true,
  enableCertificatePinning: false,
  certificatePins: [],
};

export type MobileSecurityEnv = {
  clerkPublishableKey: string;
  apiBaseUrl: string;
  appKind: "customer" | "driver";
};

export function readMobileSecurityEnv(): MobileSecurityEnv {
  return {
    clerkPublishableKey: (process.env.EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "").trim(),
    apiBaseUrl: (process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8001").replace(/\/$/, ""),
    appKind: (process.env.EXPO_PUBLIC_APP_KIND as "customer" | "driver") ?? "customer",
  };
}

export function isClerkConfigured(env = readMobileSecurityEnv()) {
  return env.clerkPublishableKey.length > 0;
}
