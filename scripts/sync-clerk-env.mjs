#!/usr/bin/env node
/**
 * Sync Clerk keys into each web/mobile app + API.
 *
 * platform_driver only — TWO Clerk apps:
 *   PorterChain Platform → website, customer, merchant (admin uses staff IdP — no Clerk keys)
 *   Porterchain Driver   → driver portal only
 *
 * Mobile Expo apps receive EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY via @clerk/expo.
 * CLERK_MODE=unified and enterprise are DELETED (exit on request).
 *
 * Usage: pnpm clerk:sync
 */
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const MARKER_START = "# --- clerk:sync (auto — run pnpm clerk:sync) ---";
const MARKER_END = "# --- end clerk:sync ---";

const CLERK_SOURCE_CANDIDATES = [
  path.join(ROOT, "env/clerk.env"),
  path.join(ROOT, "infrastructure/deploy/scripts/clerk-keys.local.env"),
];

/** Platform Clerk consumers (admin portal is staff IdP — not listed). */
const PLATFORM_PORTALS = ["customer", "merchant"];
/** API still receives admin slot aliases (empty/unused) + driver for JWT verify. */
const ALL_PORTALS = ["customer", "merchant", "admin", "driver"];

const SURFACES = [
  { name: "website", portal: "customer", file: "website/.env.local", next: true },
  { name: "customer-portal", portal: "customer", file: "apps/customer/.env.local", next: true },
  {
    name: "merchant-portal",
    portal: "merchant",
    file: "apps/merchant-portal/.env.local",
    next: true,
  },
  {
    name: "admin",
    portal: "admin",
    file: "apps/admin/.env.local",
    next: true,
    staffIdpOnly: true,
  },
  { name: "driver-portal", portal: "driver", file: "apps/driver-portal/.env.local", next: true },
  {
    name: "mobile-customer",
    portal: "customer",
    file: "apps/mobile-customer/.env",
    expo: true,
  },
  {
    name: "mobile-driver",
    portal: "driver",
    file: "apps/mobile-driver/.env",
    expo: true,
  },
];

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

function findClerkSource() {
  for (const candidate of CLERK_SOURCE_CANDIDATES) {
    if (existsSync(candidate)) return candidate;
  }
  return null;
}

/** Platform triad: explicit keys, else Admin slots (PorterChain Platform rename). */
function resolvePlatformTriad(env) {
  const pub = (
    env.CLERK_UNIFIED_PUBLISHABLE_KEY ||
    env.CLERK_PUBLISHABLE_KEY ||
    env.CLERK_ADMIN_PUBLISHABLE_KEY ||
    ""
  ).trim();
  const sec = (
    env.CLERK_UNIFIED_SECRET_KEY ||
    env.CLERK_SECRET_KEY ||
    env.CLERK_ADMIN_SECRET_KEY ||
    ""
  ).trim();
  const jwks = (
    env.CLERK_UNIFIED_JWKS_URL ||
    env.CLERK_JWKS_URL ||
    env.CLERK_ADMIN_JWKS_URL ||
    ""
  ).trim();
  return { pub, sec, jwks };
}

function resolveDriverTriad(env) {
  return {
    pub: (env.CLERK_DRIVER_PUBLISHABLE_KEY || "").trim(),
    sec: (env.CLERK_DRIVER_SECRET_KEY || "").trim(),
    jwks: (env.CLERK_DRIVER_JWKS_URL || "").trim(),
  };
}

function rejectRetiredModes(env) {
  const explicit = (env.CLERK_MODE || "").trim().toLowerCase();
  if (explicit === "enterprise") {
    console.error("CLERK_MODE=enterprise is retired (4 unrelated apps / 12-key layout).");
    console.error("Use CLERK_MODE=platform_driver only.");
    process.exit(1);
  }
  if (explicit === "unified") {
    console.error("CLERK_MODE=unified is deleted — it collapses Driver into Platform.");
    console.error("Use CLERK_MODE=platform_driver (PorterChain Platform + Porterchain Driver).");
    process.exit(1);
  }
}

function resolveMode(env) {
  const explicit = (env.CLERK_MODE || "").trim().toLowerCase();
  if (explicit === "platform_driver" || explicit === "dual" || explicit === "platform+driver") {
    return "platform_driver";
  }
  if (explicit === "" || explicit === "unified") {
    // Empty → platform_driver. Explicit unified rejected above; keep dual-detect for empty.
    return "platform_driver";
  }
  return explicit;
}

function expandPlatformDriver(env) {
  const platform = resolvePlatformTriad(env);
  const driver = resolveDriverTriad(env);
  const missing = [];
  if (!platform.pub || !platform.sec || !platform.jwks) {
    missing.push(
      "Platform: CLERK_PUBLISHABLE_KEY / CLERK_SECRET_KEY / CLERK_JWKS_URL (or CLERK_ADMIN_*)"
    );
  }
  if (!driver.pub || !driver.sec || !driver.jwks) {
    missing.push(
      "Driver: CLERK_DRIVER_PUBLISHABLE_KEY / CLERK_DRIVER_SECRET_KEY / CLERK_DRIVER_JWKS_URL"
    );
  }
  if (missing.length) {
    return { ok: false, missing };
  }

  const expanded = {
    ...env,
    CLERK_MODE: "platform_driver",
    CLERK_UNIFIED_MODE: "false",
    CLERK_PUBLISHABLE_KEY: platform.pub,
    CLERK_SECRET_KEY: platform.sec,
    CLERK_JWKS_URL: platform.jwks,
  };

  for (const portal of PLATFORM_PORTALS) {
    const p = portal.toUpperCase();
    expanded[`CLERK_${p}_PUBLISHABLE_KEY`] = platform.pub;
    expanded[`CLERK_${p}_SECRET_KEY`] = platform.sec;
    expanded[`CLERK_${p}_JWKS_URL`] = platform.jwks;
  }
  // Admin portal left Clerk — clear admin slot so API/clients do not treat admin as Platform IdP.
  expanded.CLERK_ADMIN_PUBLISHABLE_KEY = "";
  expanded.CLERK_ADMIN_SECRET_KEY = "";
  expanded.CLERK_ADMIN_JWKS_URL = "";
  expanded.CLERK_DRIVER_PUBLISHABLE_KEY = driver.pub;
  expanded.CLERK_DRIVER_SECRET_KEY = driver.sec;
  expanded.CLERK_DRIVER_JWKS_URL = driver.jwks;

  return { ok: true, env: expanded, platform, driver };
}

function portalLines(
  env,
  portal,
  { next = false, expo = false, staffIdpOnly = false, clerkDeferred = false } = {}
) {
  const mode = env.CLERK_MODE || "platform_driver";
  if (staffIdpOnly) {
    return [
      `# Portal: admin — staff IdP only (Clerk removed · mode=${mode})`,
      "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=",
      "CLERK_SECRET_KEY=",
    ];
  }
  if (clerkDeferred) {
    return [`# Portal: ${portal} mobile — Clerk deferred`, "EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY="];
  }
  const p = portal.toUpperCase();
  const pub = env[`CLERK_${p}_PUBLISHABLE_KEY`] ?? "";
  const sec = env[`CLERK_${p}_SECRET_KEY`] ?? "";
  const lines = [`# Portal: ${portal} (mode=${mode})`];
  if (expo) {
    lines.push(`EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY=${pub}`);
  }
  if (next) {
    lines.push(`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=${pub}`);
    lines.push(`CLERK_SECRET_KEY=${sec}`);
  }
  return lines;
}

function apiLines(env) {
  const mode = env.CLERK_MODE || "platform_driver";
  const lines = [
    `# API — Clerk JWT verification (mode=${mode})`,
    `CLERK_MODE=${mode}`,
    `CLERK_UNIFIED_MODE=false`,
  ];
  for (const portal of ALL_PORTALS) {
    const p = portal.toUpperCase();
    lines.push(`CLERK_${p}_SECRET_KEY=${env[`CLERK_${p}_SECRET_KEY`] ?? ""}`);
    lines.push(`CLERK_${p}_PUBLISHABLE_KEY=${env[`CLERK_${p}_PUBLISHABLE_KEY`] ?? ""}`);
    lines.push(`CLERK_${p}_JWKS_URL=${env[`CLERK_${p}_JWKS_URL`] ?? ""}`);
  }
  lines.push(`CLERK_SECRET_KEY=${env.CLERK_SECRET_KEY ?? ""}`);
  lines.push(`CLERK_PUBLISHABLE_KEY=${env.CLERK_PUBLISHABLE_KEY ?? ""}`);
  lines.push(`CLERK_JWKS_URL=${env.CLERK_JWKS_URL ?? ""}`);
  return lines;
}

function mergeSyncedBlock(existing, blockLines) {
  const block = [MARKER_START, ...blockLines, MARKER_END].join("\n");
  if (!existing) return `${block}\n`;
  const start = existing.indexOf(MARKER_START);
  const end = existing.indexOf(MARKER_END);
  if (start >= 0 && end > start) {
    return `${existing.slice(0, start)}${block}\n${existing.slice(end + MARKER_END.length).replace(/^\n/, "")}`;
  }
  return `${existing.replace(/\s*$/, "")}\n\n${block}\n`;
}

function writeSurface(surface, env) {
  const target = path.join(ROOT, surface.file);
  mkdirSync(path.dirname(target), { recursive: true });
  const existing = existsSync(target) ? readFileSync(target, "utf8") : "";
  const block = portalLines(env, surface.portal, surface);
  writeFileSync(target, mergeSyncedBlock(existing, block));
  const note = surface.staffIdpOnly
    ? " (staff IdP — Clerk keys cleared)"
    : surface.clerkDeferred
      ? " (Clerk deferred — Expo key cleared)"
      : "";
  console.log(`✓ ${surface.name} → ${surface.file}${note}`);
}

function writeApi(env) {
  const target = path.join(ROOT, "apps/api/.env");
  const existing = existsSync(target) ? readFileSync(target, "utf8") : "";
  writeFileSync(target, mergeSyncedBlock(existing, apiLines(env)));
  console.log("✓ api → apps/api/.env");
}

function main() {
  const source = findClerkSource();
  if (!source) {
    console.error("No Clerk keys found. Create one of:");
    for (const c of CLERK_SOURCE_CANDIDATES) console.error(`  ${path.relative(ROOT, c)}`);
    process.exit(1);
  }

  let env = parseEnv(readFileSync(source, "utf8"));
  rejectRetiredModes(env);
  const mode = resolveMode(env);

  if (mode !== "platform_driver") {
    console.error(`Unknown CLERK_MODE=${mode}. Only platform_driver is supported.`);
    process.exit(1);
  }

  const expanded = expandPlatformDriver(env);
  if (!expanded.ok) {
    console.error("CLERK_MODE=platform_driver requires:");
    for (const key of expanded.missing) console.error(`  ${key}`);
    process.exit(1);
  }
  const same =
    expanded.platform.sec === expanded.driver.sec &&
    expanded.platform.jwks === expanded.driver.jwks;
  console.log("Mode: platform_driver (PorterChain Platform + Porterchain Driver)\n");
  if (same) {
    console.log(
      "Note: Driver keys match Platform (OK for local until Driver DEV instance exists).\n"
    );
  } else {
    console.log("Driver keys are distinct from Platform.\n");
  }

  env = expanded.env;

  if (source !== path.join(ROOT, "env/clerk.env")) {
    mkdirSync(path.join(ROOT, "env"), { recursive: true });
    copyFileSync(source, path.join(ROOT, "env/clerk.env"));
    console.log(`✓ copied ${path.relative(ROOT, source)} → env/clerk.env`);
  }

  console.log(`Syncing Clerk keys from ${path.relative(ROOT, source)}...\n`);
  for (const surface of SURFACES) writeSurface(surface, env);
  writeApi(env);
  console.log("\nDone. Restart dev servers if running.");
  console.log(
    "Platform portals share Platform pk; driver portal uses CLERK_DRIVER publishable key."
  );
  console.log(
    "Secrets stay server-only (CLERK_SECRET_KEY). Never put sk_ in browser/mobile bundles."
  );
}

main();
