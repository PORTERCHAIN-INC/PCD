import * as Sentry from "@sentry/nextjs";

function pickEnv(...keys: string[]): string {
  for (const key of keys) {
    const value = process.env[key]?.trim();
    if (value) return value;
  }
  return "";
}

type PortalSentryOptions = NonNullable<Parameters<typeof Sentry.init>[0]>;

/** Shared Sentry options for Next.js portals (DD-02). Returns null when DSN is unset. */
export function portalSentryOptions(serviceName: string): PortalSentryOptions | null {
  const dsn = pickEnv("NEXT_PUBLIC_SENTRY_DSN", "SENTRY_DSN");
  if (!dsn) return null;

  const environment =
    pickEnv("NEXT_PUBLIC_APP_ENV", "APP_ENV", "NODE_ENV") || "development";

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

export function initPortalSentry(serviceName: string): void {
  const options = portalSentryOptions(serviceName);
  if (options) {
    Sentry.init(options);
  }
}
