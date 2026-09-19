#!/usr/bin/env node
/**
 * Print EAS secret commands for mobile store builds.
 * Publishable keys only — never upload Clerk secret keys to EAS.
 *
 * Usage: pnpm clerk:eas
 */
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SOURCE = path.join(ROOT, "env/clerk.env");

function parseEnv(content) {
  const out = {};
  for (const line of content.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq <= 0) continue;
    const key = trimmed.slice(0, eq).trim();
    let value = trimmed.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    out[key] = value;
  }
  return out;
}

if (!existsSync(SOURCE)) {
  console.error("Missing env/clerk.env — copy env/clerk.env.example first.");
  process.exit(1);
}

const env = parseEnv(readFileSync(SOURCE, "utf8"));
const customer = env.CLERK_CUSTOMER_PUBLISHABLE_KEY || env.CLERK_PUBLISHABLE_KEY || "";
const driver = env.CLERK_DRIVER_PUBLISHABLE_KEY || "";

if (!customer || !driver) {
  console.error(
    "clerk.env is missing CLERK_CUSTOMER_PUBLISHABLE_KEY or CLERK_DRIVER_PUBLISHABLE_KEY."
  );
  process.exit(1);
}

console.log(`# Run after \`eas init\` in each app. Publishable keys only.

cd apps/mobile-customer
eas secret:create --scope project --name EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY --value ${JSON.stringify(customer)} --force

cd ../mobile-driver
eas secret:create --scope project --name EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY --value ${JSON.stringify(driver)} --force

# Native FCM (store builds, not Expo Go):
# Driver  = com.porterchain.PCD
# Customer = com.porterchain.customer
# iOS plists are already in each app. Drop Android google-services.json next.
`);
