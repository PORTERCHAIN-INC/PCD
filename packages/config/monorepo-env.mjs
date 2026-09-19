import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

/** Porterchain Clerk application per user class (§0.5). */
export const CLERK_PORTALS = ["customer", "merchant", "admin", "driver"];

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
  const clerkPath = path.resolve(cwd, "../../env/clerk.env");
  loadEnvFile(envPath);
  loadEnvFile(clerkPath);
  return envPath;
}

function pick(...keys) {
  for (const key of keys) {
    const value = process.env[key]?.trim();
    if (value) return value;
  }
  return "";
}

function isLocalAppEnv() {
  const appEnv = (process.env.NEXT_PUBLIC_APP_ENV || process.env.APP_ENV || "").toLowerCase();
  return appEnv === "local" || appEnv === "development" || appEnv === "dev";
}

function isLiveClerkValue(value) {
  return (
    typeof value === "string" && (value.includes("_live_") || value.includes(".porterchain.com"))
  );
}

/**
 * Resolve Clerk keys for one portal (customer | merchant | admin | driver).
 * Local safety: ambient shell/Doppler `pk_live_*` must not override `.env.local` / test keys
 * when APP_ENV is local (localhost cannot use production Clerk domains).
 */
export function clerkKeysForPortal(portal) {
  const p = portal.toUpperCase();
  const portalPub = process.env[`CLERK_${p}_PUBLISHABLE_KEY`]?.trim() || "";
  const nextPub = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.trim() || "";
  const genericPub = process.env.CLERK_PUBLISHABLE_KEY?.trim() || "";
  const portalSecret = process.env[`CLERK_${p}_SECRET_KEY`]?.trim() || "";
  const nextSecret = process.env.CLERK_SECRET_KEY?.trim() || "";
  const portalJwks = process.env[`CLERK_${p}_JWKS_URL`]?.trim() || "";
  const genericJwks = process.env.CLERK_JWKS_URL?.trim() || "";

  let publishable = portalPub || nextPub || genericPub;
  let secret = portalSecret || nextSecret;
  let jwks = portalJwks || genericJwks;

  if (
    isLocalAppEnv() &&
    isLiveClerkValue(portalPub) &&
    (nextPub.includes("pk_test") || genericPub.includes("pk_test"))
  ) {
    publishable = nextPub.includes("pk_test") ? nextPub : genericPub;
    if (nextSecret.includes("sk_test")) secret = nextSecret;
    if (jwks.includes("porterchain.com") && !jwks.includes("accounts.dev")) {
      jwks = "";
    }
  }

  return { publishable, secret, jwks };
}

/** Next.js env block for a portal — publishable key only (baked at build). */
export function portalPublicEnv(portal, extras = {}) {
  const clerk = clerkKeysForPortal(portal);
  const base = nextPublicEnv();
  return {
    ...base,
    ...extras,
    NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: clerk.publishable || base.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY,
    // CLERK_SECRET_KEY must NOT be listed here — Docker runtime env only (not build-time).
  };
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
      "CLERK_CUSTOMER_PUBLISHABLE_KEY",
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

/** Website — shares porterchain-customer Clerk app. */
export function websitePublicEnv() {
  return portalPublicEnv("customer", {
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
    NEXT_PUBLIC_CLERK_DEV_BYPASS: pick("NEXT_PUBLIC_CLERK_DEV_BYPASS", "CLERK_DEV_BYPASS"),
    NEXT_PUBLIC_CLERK_SIGN_IN_URL: pick("NEXT_PUBLIC_CLERK_SIGN_IN_URL") || "/sign-in",
    NEXT_PUBLIC_CLERK_SIGN_IN_FORCE_REDIRECT_URL:
      pick("NEXT_PUBLIC_CLERK_SIGN_IN_FORCE_REDIRECT_URL") || "/dashboard",
    NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL:
      pick("NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL") || "/dashboard",
    NEXT_PUBLIC_CLERK_AFTER_SIGN_OUT_URL:
      pick("NEXT_PUBLIC_CLERK_AFTER_SIGN_OUT_URL") || "/sign-in",
  });
}

/** Merchant portal. */
export function merchantPublicEnv() {
  return portalPublicEnv("merchant", {
    NEXT_PUBLIC_CLERK_SIGN_IN_URL: pick("NEXT_PUBLIC_CLERK_SIGN_IN_URL") || "/sign-in",
    NEXT_PUBLIC_CLERK_SIGN_IN_FORCE_REDIRECT_URL:
      pick("NEXT_PUBLIC_CLERK_SIGN_IN_FORCE_REDIRECT_URL") || "/onboarding",
    NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL:
      pick("NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL") || "/onboarding",
  });
}

/** Driver web portal. */
export function driverPublicEnv() {
  return portalPublicEnv("driver");
}

/** Customer portal extras. */
export function customerPublicEnv() {
  return portalPublicEnv("customer", {
    NEXT_PUBLIC_WEBSITE_URL: pick("NEXT_PUBLIC_WEBSITE_URL", "WEBSITE_URL"),
    NEXT_PUBLIC_CLERK_SIGN_IN_URL: pick("NEXT_PUBLIC_CLERK_SIGN_IN_URL") || "/sign-in",
    NEXT_PUBLIC_CLERK_SIGN_IN_FORCE_REDIRECT_URL:
      pick("NEXT_PUBLIC_CLERK_SIGN_IN_FORCE_REDIRECT_URL") || "/dashboard",
    NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL:
      pick("NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL") || "/dashboard",
  });
}
