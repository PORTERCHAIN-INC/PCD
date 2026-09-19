/**
 * Shared Playwright fixtures for Admin P0 e2e.
 *
 * Live path (Jeff slice — real staff handshake):
 *   ADMIN_RUN_LIVE=1
 *   ADMIN_STORAGE_STATE=e2e/.auth/staff.json
 *   # or inject HttpOnly cookie without codegen:
 *   ADMIN_STAFF_SID=<pc_staff_sid value>
 *
 * Local bypass path (dev shell only):
 *   Admin must run with NEXT_PUBLIC_CLERK_DEV_BYPASS=true
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
  const registryPath = path.join(process.cwd(), "../../docs/testing/admin_p0_registry.json");
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
  if (statePath && fs.existsSync(statePath)) return true;
  return Boolean(process.env.ADMIN_STAFF_SID?.trim());
}

/**
 * Resolve Playwright storageState for staff IdP.
 * Prefer ADMIN_STORAGE_STATE file; else build cookie jar from ADMIN_STAFF_SID;
 * else empty jar (Clerk/staff bypass on a local admin build).
 */
export function resolveStaffStorageState(): StaffStorageState {
  const statePath = process.env.ADMIN_STORAGE_STATE?.trim();
  if (statePath) {
    if (!fs.existsSync(statePath)) {
      throw new Error(`ADMIN_STORAGE_STATE not found: ${statePath}`);
    }
    return statePath;
  }

  const sid = process.env.ADMIN_STAFF_SID?.trim();
  if (sid) {
    const url = new URL(adminBaseUrl());
    return {
      cookies: [
        {
          name: "pc_staff_sid",
          value: sid,
          domain: url.hostname,
          path: "/",
          httpOnly: true,
          secure: url.protocol === "https:",
          sameSite: "Lax",
          expires: Math.floor(Date.now() / 1000) + 60 * 60 * 24 * 7,
        },
      ],
      origins: [],
    };
  }

  return { cookies: [], origins: [] };
}

/** Soft-skip unless live; hard-fail live runs when auth env is missing. */
export function requireLiveStaffAuth(): void {
  test.skip(!liveEnabled, "Set ADMIN_RUN_LIVE=1 for the live admin golden path");
  if (!hasStaffAuth()) {
    throw new Error(
      "Set ADMIN_STORAGE_STATE (Playwright cookie jar) or ADMIN_STAFF_SID (pc_staff_sid value)"
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
