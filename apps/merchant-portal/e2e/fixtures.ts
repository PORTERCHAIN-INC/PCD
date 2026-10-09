/**
 * Shared Playwright fixtures for Merchant P0 e2e.
 *
 * Live golden path:
 *   pnpm --filter @porterchain/merchant-portal test:e2e:install
 *   MERCHANT_E2E_LIVE=1 \
 *   MERCHANT_STORAGE_STATE_DISPATCHER=e2e/.auth/dispatcher.json \
 *   MERCHANT_STORAGE_STATE_VIEWER=e2e/.auth/viewer.json \
 *   pnpm test:merchant-p0:live
 *
 * Capture jars (from apps/merchant-portal):
 *   pnpm test:e2e:codegen:dispatcher
 *   pnpm test:e2e:codegen:viewer
 */

import fs from "fs";
import path from "path";
import { test as base, expect, type Page, type APIRequestContext } from "@playwright/test";

export type P0Case = {
  id: string;
  title: string;
  persona: string;
  layer: string;
  runner: string;
  status: string;
  covers?: string[];
};

export type MerchantSeat = "dispatcher" | "viewer" | "owner";

function loadRegistry(): { cases: P0Case[] } {
  const registryPath = path.join(process.cwd(), "../../docs/testing/merchant_p0_registry.json");
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

export function tcId(id: string): string {
  return `@${id}`;
}

export const liveEnabled = Boolean(process.env.MERCHANT_E2E_LIVE);

function envStoragePath(role: MerchantSeat): string | undefined {
  const keyed =
    role === "dispatcher"
      ? process.env.MERCHANT_STORAGE_STATE_DISPATCHER
      : role === "viewer"
        ? process.env.MERCHANT_STORAGE_STATE_VIEWER
        : process.env.MERCHANT_STORAGE_STATE_OWNER;
  return keyed || process.env.MERCHANT_STORAGE_STATE || undefined;
}

/** Absolute path only when the cookie jar file exists on disk. */
export function storageStatePath(role: MerchantSeat): string | undefined {
  const raw = envStoragePath(role);
  if (!raw) return undefined;
  const resolved = path.isAbsolute(raw) ? raw : path.resolve(process.cwd(), raw);
  return fs.existsSync(resolved) ? resolved : undefined;
}

/**
 * Local stack only: the merchant portal dev auth (Bearer "dev") signs in as the seeded
 * owner seat, so dispatcher/owner journeys can run without a Clerk jar. Viewer-role checks
 * still need a real viewer jar.
 */
export const localBypass = process.env.MERCHANT_E2E_LOCAL_BYPASS === "1";

/** Describe-level gate — skips before Chromium launch. */
export function liveReady(role: MerchantSeat): boolean {
  if (!liveEnabled) return false;
  if (storageStatePath(role)) return true;
  return localBypass && role !== "viewer";
}

export function liveSkipReason(role: MerchantSeat): string {
  if (!liveEnabled) return "Set MERCHANT_E2E_LIVE=1";
  if (!envStoragePath(role)) {
    return `Set MERCHANT_STORAGE_STATE_${role.toUpperCase()} to a Clerk storageState JSON`;
  }
  return `Storage jar missing on disk for ${role} — run pnpm test:e2e:codegen:${role} and sign in`;
}

export const apiBase = () =>
  (
    process.env.MERCHANT_API_BASE ||
    process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ||
    "http://localhost:8001"
  ).replace(/\/$/, "");

/** Capture the first Clerk bearer the portal attaches to API calls. */
export async function captureBearer(page: Page, seedPath = "/dashboard"): Promise<string> {
  let bearer: string | undefined;
  page.on("request", (req) => {
    const auth = req.headers()["authorization"];
    if (auth?.toLowerCase().startsWith("bearer ")) {
      bearer = auth.slice(7).trim();
    }
  });
  await page.goto(seedPath);
  await page.waitForLoadState("networkidle").catch(() => undefined);
  await page.waitForTimeout(1500);
  if (!bearer) {
    bearer = await page.evaluate(async () => {
      const clerk = (
        window as unknown as { Clerk?: { session?: { getToken: () => Promise<string | null> } } }
      ).Clerk;
      const token = await clerk?.session?.getToken?.();
      return token || "";
    });
  }
  if (!bearer) {
    throw new Error("Could not capture Clerk bearer — is storageState a signed-in merchant seat?");
  }
  return bearer;
}

export async function merchantApi<T>(
  request: APIRequestContext,
  bearer: string,
  method: "GET" | "POST",
  pathName: string,
  body?: unknown
): Promise<{ status: number; json: T }> {
  const res = await request.fetch(`${apiBase()}${pathName}`, {
    method,
    headers: {
      Authorization: `Bearer ${bearer}`,
      "Content-Type": "application/json",
    },
    data: body === undefined ? undefined : body,
  });
  const json = (await res.json().catch(() => ({}))) as T;
  return { status: res.status(), json };
}

export function gtaBookPayload() {
  const scheduled_at = new Date().toISOString();
  return {
    pickup: {
      formatted: "100 King St W, Toronto, ON M5X 1A1",
      postal: "M5X 1A1",
      lat: 43.6488,
      lng: -79.3817,
    },
    dropoff: {
      formatted: "200 Bay St, Toronto, ON M5J 2J2",
      postal: "M5J 2J2",
      lat: 43.6466,
      lng: -79.3795,
    },
    vehicle_class: "cargo_van",
    package_type: "looseParcel",
    scheduled_at,
    schedule_mode: "now",
    is_sandbox: true,
  };
}
