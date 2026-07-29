#!/usr/bin/env node
/**
 * Sync Clerk keys into each web/mobile app + API.
 *
 * Unified only (PorterChain Platform triad):
 *   CLERK_PUBLISHABLE_KEY / CLERK_SECRET_KEY / CLERK_JWKS_URL
 *   If triad missing, derived from CLERK_ADMIN_* (Platform rename path)
 *   (optional aliases: CLERK_UNIFIED_*)
 *
 * Expands the Platform triad into per-portal CLERK_{PORTAL}_* slot aliases
 * for dual-read / compose compat during transition.
 *
 * CLERK_MODE=enterprise (legacy 4-app / 12-key) is retired — see
 * docs/runbooks/clerk-consolidation.md.
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

const PORTALS = ["customer", "merchant", "admin", "driver"];

const SURFACES = [
  { name: "website", portal: "customer", file: "website/.env.local", next: true },
  { name: "customer-portal", portal: "customer", file: "apps/customer/.env.local", next: true },
  {
    name: "merchant-portal",
    portal: "merchant",
    file: "apps/merchant-portal/.env.local",
    next: true,
  },
  { name: "admin", portal: "admin", file: "apps/admin/.env.local", next: true },
  { name: "driver-portal", portal: "driver", file: "apps/driver-portal/.env.local", next: true },
  { name: "mobile-customer", portal: "customer", file: "apps/mobile-customer/.env", expo: true },
  { name: "mobile-driver", portal: "driver", file: "apps/mobile-driver/.env", expo: true },
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

/** Platform triad: explicit unified keys, else Admin slots (ex Porterchain Admin). */
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

function rejectEnterpriseMode(env) {
  const explicit = (env.CLERK_MODE || "").trim().toLowerCase();
  if (explicit === "enterprise") {
    console.error(
      "CLERK_MODE=enterprise is retired (4-app / 12-key layout is no longer supported)."
    );
    console.error(
      "Use unified PorterChain Platform only. See docs/runbooks/clerk-consolidation.md"
    );
    process.exit(1);
  }
}

function expandUnified(env) {
  const { pub, sec, jwks } = resolvePlatformTriad(env);
  if (!pub || !sec || !jwks) {
    return {
      ok: false,
      missing: [
        "CLERK_PUBLISHABLE_KEY (or CLERK_ADMIN_PUBLISHABLE_KEY)",
        "CLERK_SECRET_KEY (or CLERK_ADMIN_SECRET_KEY)",
        "CLERK_JWKS_URL (or CLERK_ADMIN_JWKS_URL)",
      ],
    };
  }
  const expanded = { ...env, CLERK_MODE: "unified", CLERK_UNIFIED_MODE: "true" };
  for (const portal of PORTALS) {
    const p = portal.toUpperCase();
    expanded[`CLERK_${p}_PUBLISHABLE_KEY`] = pub;
    expanded[`CLERK_${p}_SECRET_KEY`] = sec;
    expanded[`CLERK_${p}_JWKS_URL`] = jwks;
  }
  expanded.CLERK_PUBLISHABLE_KEY = pub;
  expanded.CLERK_SECRET_KEY = sec;
  expanded.CLERK_JWKS_URL = jwks;
  return { ok: true, env: expanded, pub, sec, jwks };
}

function portalLines(env, portal, { next = false, expo = false } = {}) {
  const p = portal.toUpperCase();
  const pub = env[`CLERK_${p}_PUBLISHABLE_KEY`] ?? "";
  const sec = env[`CLERK_${p}_SECRET_KEY`] ?? "";
  const lines = [`# Portal: ${portal} (mode=unified)`];
  if (expo) {
    lines.push(`EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY=${pub}`);
  }
  if (next) {
    lines.push(`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=${pub}`);
    // Server-only — never NEXT_PUBLIC_
    lines.push(`CLERK_SECRET_KEY=${sec}`);
  }
  return lines;
}

function apiLines(env) {
  const lines = [`# API — Clerk JWT verification (mode=unified)`, `CLERK_UNIFIED_MODE=true`];
  for (const portal of PORTALS) {
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
  console.log(`✓ ${surface.name} → ${surface.file}`);
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
  rejectEnterpriseMode(env);

  const expanded = expandUnified(env);
  if (!expanded.ok) {
    console.error(`CLERK_MODE=unified requires PorterChain Platform triad:`);
    for (const key of expanded.missing) console.error(`  ${key}`);
    process.exit(1);
  }
  env = expanded.env;
  console.log("Mode: unified (PorterChain Platform — one publishable key for all clients)\n");

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
    "Clients share one NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY / EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY."
  );
  console.log(
    "Secrets stay server-only (CLERK_SECRET_KEY). Never put sk_ in browser/mobile bundles."
  );
}

main();
