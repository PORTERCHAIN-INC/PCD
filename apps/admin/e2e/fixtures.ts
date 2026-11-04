/**
 * Shared Playwright fixtures for Admin P0 e2e.
 *
 * Live path (Jeff slice — real staff handshake):
 *   ADMIN_RUN_LIVE=1
 *   ADMIN_STORAGE_STATE=e2e/.auth/staff.json
 *   (Keycloak session cookies, captured after a real pc-admin login incl. TOTP)
 *
 * Local bypass path (dev shell only):
 *   Admin must run with NEXT_PUBLIC_AUTH_DEV_BYPASS=true
 *   Empty storageState is enough — middleware + AdminAuthProvider use Bearer "dev".
 *
 * Capture storageState once while signed in:
 *   mkdir -p e2e/.auth
 *   pnpm exec playwright codegen http://localhost:3002/dashboard --save-storage=e2e/.auth/staff.json
 */
import fs from "fs";
import path from "path";
import { test as base, expect, type Page } from "@playwright/test";

export type P0Case = {
  id: string;
  title: string;
  persona: string;
  layer: string;
  runner: string;
  status: string;
  covers?: string[];
};

export type StaffStorageState =
  | string
  | {
      cookies: Array<{
        name: string;
        value: string;
        domain: string;
        path: string;
        httpOnly: boolean;
        secure: boolean;
        sameSite: "Strict" | "Lax" | "None";
        expires: number;
      }>;
      origins: unknown[];
    };

function loadRegistry(): { cases: P0Case[] } {
  const registryPath = path.resolve(__dirname, "../../../docs/testing/admin_p0_registry.json");
  return JSON.parse(fs.readFileSync(registryPath, "utf8")) as { cases: P0Case[] };
}

const registry = loadRegistry();

export function playwrightCases(status?: "skeleton" | "implemented"): P0Case[] {
  return registry.cases.filter(
    (c) => c.runner === "playwright" && (status ? c.status === status : true)
  );
}

export const test = base;
export { expect };

/** Mark a test with the SSOT case id for grep: `--grep @AUTH-001` */
export function tcId(id: string): string {
  return `@${id}`;
}

export const liveEnabled = Boolean(process.env.ADMIN_RUN_LIVE);

export function adminBaseUrl(): string {
  return (process.env.ADMIN_BASE_URL || "http://localhost:3002").replace(/\/$/, "");
}

/** True when a real staff cookie jar or sid is configured (not empty bypass). */
export function hasStaffAuth(): boolean {
  const statePath = process.env.ADMIN_STORAGE_STATE?.trim();
  return Boolean(statePath && fs.existsSync(statePath));
}

/**
 * Resolve Playwright storageState for staff IdP.
 * Prefer ADMIN_STORAGE_STATE file (Keycloak session);
 * else empty jar (Keycloak/staff bypass on a local admin build).
 */
export function resolveStaffStorageState(): StaffStorageState {
  const statePath = process.env.ADMIN_STORAGE_STATE?.trim();
  if (statePath) {
    if (!fs.existsSync(statePath)) {
      throw new Error(`ADMIN_STORAGE_STATE not found: ${statePath}`);
    }
    return statePath;
  }

  return { cookies: [], origins: [] };
}

/** Soft-skip unless live; hard-fail live runs when auth env is missing. */
function requireLiveStaffAuth(): void {
  test.skip(!liveEnabled, "Set ADMIN_RUN_LIVE=1 for the live admin golden path");
  if (!hasStaffAuth()) {
    throw new Error(
      "Set ADMIN_STORAGE_STATE (Playwright cookie jar from a Keycloak pc-admin login)"
    );
  }
}

/**
 * Probe admin origin. Soft-skips when portal is down unless ADMIN_RUN_LIVE=1
 * (then throws — live runs must not silently pass).
 */
export async function ensureAdminReachable(page: Page): Promise<void> {
  const probe = await page.request.get("/", { failOnStatusCode: false }).catch(() => null);
  const up = Boolean(probe && probe.status() < 500);
  if (up) return;
  if (liveEnabled) {
    throw new Error(`Admin portal not reachable at ${adminBaseUrl()}`);
  }
  test.skip(true, "Admin portal not reachable on ADMIN_BASE_URL");
}

/**
 * Open an admin path with a staff session. On a local stack the sign-in page offers
 * "Continue as Local Super Admin" (mints a real local staff session); use it when no
 * storage state / sid was provided. Skips (or fails when ADMIN_RUN_LIVE=1) if neither works.
 */
export async function gotoAsStaff(page: Page, pathname: string): Promise<void> {
  await page.goto(pathname);
  const localButton = page.getByRole("button", { name: /continue as local super admin/i });
  const onSignIn = await localButton
    .waitFor({ state: "visible", timeout: 5_000 })
    .then(() => true)
    .catch(() => false);
  if (!onSignIn) return;
  await localButton.click();
  await page
    .waitForURL((url) => !/sign-?in|login/i.test(url.pathname), { timeout: 20_000 })
    .catch(() => undefined);
  await page.goto(pathname);
  const stillSignIn = await page
    .getByRole("heading", { name: /staff sign-in/i })
    .isVisible()
    .catch(() => false);
  if (stillSignIn) {
    if (liveEnabled) throw new Error("Local staff sign-in did not create a session");
    test.skip(true, "No staff session (set ADMIN_STORAGE_STATE or run the local stack)");
  }
}
