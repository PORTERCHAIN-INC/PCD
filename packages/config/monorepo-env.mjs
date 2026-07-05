import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

/** Load monorepo `env/.env` (does not override vars already set in process.env). */
export function loadMonorepoEnv(cwd, relativeEnvPath = "../../env/.env") {
  const envPath = path.resolve(cwd, relativeEnvPath);
  if (!existsSync(envPath)) return envPath;
  for (const line of readFileSync(envPath, "utf8").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq <= 0) continue;
    const key = trimmed.slice(0, eq).trim();
    if (process.env[key] !== undefined) continue;
    let value = trimmed.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    process.env[key] = value;
  }
  return envPath;
}

function pick(...keys) {
  for (const key of keys) {
    const value = process.env[key]?.trim();
    if (value) return value;
  }
  return "";
}

/** Shared NEXT_PUBLIC_* vars injected into Next.js client bundles. */
export function nextPublicEnv() {
  return {
    NEXT_PUBLIC_GOOGLE_MAPS_API_KEY: pick(
      "NEXT_PUBLIC_GOOGLE_MAPS_API_KEY",
      "GOOGLE_MAPS_BROWSER_API_KEY"
    ),
    NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: pick(
      "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY",
      "CLERK_PUBLISHABLE_KEY"
    ),
    NEXT_PUBLIC_PORTERCHAIN_API_URL: pick(
      "NEXT_PUBLIC_PORTERCHAIN_API_URL",
      "NEXT_PUBLIC_API_URL",
      "PORTERCHAIN_API_URL"
    ),
    NEXT_PUBLIC_CONTACT_EMAIL: pick("NEXT_PUBLIC_CONTACT_EMAIL"),
    NEXT_PUBLIC_SITE_URL: pick("NEXT_PUBLIC_SITE_URL"),
    NEXT_PUBLIC_ZOHO_SALESIQ_ENABLED: pick("NEXT_PUBLIC_ZOHO_SALESIQ_ENABLED"),
    NEXT_PUBLIC_ZOHO_SALESIQ_WIDGET_CODE: pick("NEXT_PUBLIC_ZOHO_SALESIQ_WIDGET_CODE"),
    NEXT_PUBLIC_SENTRY_DSN: pick("NEXT_PUBLIC_SENTRY_DSN", "SENTRY_DSN"),
    NEXT_PUBLIC_APP_ENV: pick("NEXT_PUBLIC_APP_ENV", "APP_ENV") || "local",
  };
}

/** Admin portal extras. */
export function adminPublicEnv() {
  return {
    ...nextPublicEnv(),
    NEXT_PUBLIC_APP_ENV: pick("NEXT_PUBLIC_APP_ENV", "APP_ENV") || "local",
    NEXT_PUBLIC_CLERK_DEV_BYPASS: pick("NEXT_PUBLIC_CLERK_DEV_BYPASS", "CLERK_DEV_BYPASS"),
  };
}

/** Customer portal extras. */
export function customerPublicEnv() {
  return {
    ...nextPublicEnv(),
    NEXT_PUBLIC_WEBSITE_URL: pick("NEXT_PUBLIC_WEBSITE_URL", "WEBSITE_URL"),
  };
}
