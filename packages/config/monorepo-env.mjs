import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

/** Keycloak OIDC client per surface (realm porterchain). */
export const KEYCLOAK_CLIENTS = {
  website: "pc-website",
  customer: "pc-customer-portal",
  merchant: "pc-merchant-portal",
  admin: "pc-admin",
  driver: "pc-driver-portal",
};

function parseEnvLines(content) {
  for (const line of content.split("\n")) {
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
}

function loadEnvFile(filePath) {
  if (!existsSync(filePath)) return false;
  parseEnvLines(readFileSync(filePath, "utf8"));
  return true;
}

/** Load monorepo env files (does not override vars already set in process.env). */
export function loadMonorepoEnv(cwd, relativeEnvPath = "../../env/.env") {
  const envPath = path.resolve(cwd, relativeEnvPath);
  loadEnvFile(envPath);
  return envPath;
}

function pick(...keys) {
  for (const key of keys) {
    const value = process.env[key]?.trim();
    if (value) return value;
  }
  return "";
}

/** Next.js env block for one surface: Keycloak client id (public) + shared vars. */
export function portalPublicEnv(portal, extras = {}) {
  return {
    ...nextPublicEnv(),
    ...extras,
    NEXT_PUBLIC_KEYCLOAK_CLIENT_ID:
      pick("NEXT_PUBLIC_KEYCLOAK_CLIENT_ID", "KEYCLOAK_CLIENT_ID") ||
      KEYCLOAK_CLIENTS[portal] ||
      "",
    // AUTH_SESSION_SECRET / KEYCLOAK_CLIENT_SECRET must NOT be listed here (runtime env only).
  };
}

/** Shared NEXT_PUBLIC_* vars injected into Next.js client bundles. */
export function nextPublicEnv() {
  return {
    NEXT_PUBLIC_PORTERCHAIN_API_URL: pick(
      "NEXT_PUBLIC_PORTERCHAIN_API_URL",
      "NEXT_PUBLIC_API_URL",
      "PORTERCHAIN_API_URL"
    ),
    NEXT_PUBLIC_CONTACT_EMAIL: pick("NEXT_PUBLIC_CONTACT_EMAIL"),
    NEXT_PUBLIC_SITE_URL: pick("NEXT_PUBLIC_SITE_URL"),
    NEXT_PUBLIC_ZOHO_SALESIQ_ENABLED: pick("NEXT_PUBLIC_ZOHO_SALESIQ_ENABLED"),
    NEXT_PUBLIC_ZOHO_SALESIQ_WIDGET_CODE: pick("NEXT_PUBLIC_ZOHO_SALESIQ_WIDGET_CODE"),
    NEXT_PUBLIC_GLITCHTIP_DSN: pick("NEXT_PUBLIC_GLITCHTIP_DSN", "GLITCHTIP_DSN"),
    NEXT_PUBLIC_APP_ENV: pick("NEXT_PUBLIC_APP_ENV", "APP_ENV") || "local",
  };
}

/** Website (Keycloak pc-website client). */
export function websitePublicEnv() {
  return portalPublicEnv("website", {
    NEXT_PUBLIC_ADMIN_PORTAL_URL: pick("NEXT_PUBLIC_ADMIN_PORTAL_URL") || "http://localhost:3002",
    NEXT_PUBLIC_MERCHANT_PORTAL_URL:
      pick("NEXT_PUBLIC_MERCHANT_PORTAL_URL") || "http://localhost:3001",
    NEXT_PUBLIC_CUSTOMER_PORTAL_URL:
      pick("NEXT_PUBLIC_CUSTOMER_PORTAL_URL") || "http://localhost:3004",
    NEXT_PUBLIC_DRIVER_PORTAL_URL: pick("NEXT_PUBLIC_DRIVER_PORTAL_URL") || "http://localhost:3003",
  });
}

/** Admin portal extras. */
export function adminPublicEnv() {
  return portalPublicEnv("admin", {
    NEXT_PUBLIC_APP_ENV: pick("NEXT_PUBLIC_APP_ENV", "APP_ENV") || "local",
  });
}

/** Merchant portal. */
export function merchantPublicEnv() {
  return portalPublicEnv("merchant");
}

/** Driver web portal. */
export function driverPublicEnv() {
  return portalPublicEnv("driver");
}

/** Customer portal extras. */
export function customerPublicEnv() {
  return portalPublicEnv("customer", {
    NEXT_PUBLIC_WEBSITE_URL: pick("NEXT_PUBLIC_WEBSITE_URL", "WEBSITE_URL"),
  });
}
