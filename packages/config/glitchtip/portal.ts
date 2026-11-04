// GlitchTip error tracking (self-hosted, doc 36). GlitchTip speaks the Sentry protocol, so the
// Sentry SDK is the client; only the DSN points at our GlitchTip. Off when the DSN is unset.
import * as ErrorSdk from "@sentry/nextjs";

function pickEnv(...keys: string[]): string {
  for (const key of keys) {
    const value = process.env[key]?.trim();
    if (value) return value;
  }
  return "";
}

type PortalErrorTrackingOptions = NonNullable<Parameters<typeof ErrorSdk.init>[0]>;

/** Shared GlitchTip options for Next.js portals (DD-02). Returns null when the DSN is unset. */
export function portalErrorTrackingOptions(serviceName: string): PortalErrorTrackingOptions | null {
  const dsn = pickEnv("NEXT_PUBLIC_GLITCHTIP_DSN", "GLITCHTIP_DSN");
  if (!dsn) return null;

  const environment = pickEnv("NEXT_PUBLIC_APP_ENV", "APP_ENV", "NODE_ENV") || "development";

  return {
    dsn,
    environment,
    tracesSampleRate: environment === "production" ? 0.2 : 1.0,
    sendDefaultPii: false,
    initialScope: {
      tags: { service: serviceName },
    },
  };
}

export function initPortalErrorTracking(serviceName: string): void {
  const options = portalErrorTrackingOptions(serviceName);
  if (options) {
    ErrorSdk.init(options);
  }
}

/** Next.js onRequestError hook; a no-op until init has run. */
export const captureRequestError = ErrorSdk.captureRequestError;
