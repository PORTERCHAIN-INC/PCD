/**
 * UI-OPS-006 — Optimize tab smoke (day plan copy + pool → preview → commit).
 *
 * Requires admin on ADMIN_BASE_URL (default :3002) with local Clerk/API bypass.
 * BFF + optimize APIs are mocked.
 *
 *   ADMIN_RUN_LIVE=1 pnpm --filter @porterchain/admin test:e2e -- e2e/optimize.p0.spec.ts
 */
import { test, expect, tcId, ensureAdminReachable } from "./fixtures";

// Prefer system Chrome when Playwright's bundled Chromium isn't installed yet.
test.use(process.env.PW_CHANNEL === "chromium" ? {} : { channel: "chrome" });

const SESSION = {
  user_id: "user-e2e-opt",
  email: "ops@porterchain.test",
  status: "active",
  onboarding_status: "complete",
  roles: ["dispatcher"],
  permissions: ["system:all", "platform.admin.access", "dispatch", "dispatch_read", "dashboard"],
  modules: ["dispatch", "dispatch_read", "dashboard"],
  workspaces: [{ id: "platform", kind: "platform", label: "PorterChain" }],
  default_workspace: "platform",
  legacy_profile_ids: { admin_user_id: "adm-e2e-opt" },
};

const POOL = {
  order_count: 2,
  vehicle_count: 1,
  driver_count: 1,
  merchants: [{ merchant_id: "mer-1", order_count: 2 }],
  vehicle_ids: ["vehicle_abc123xyz"],
  placeholder_skipped: 0,
};

const READY = {
  ok: true,
  status: "ready",
  run_id: "run-e2e-1",
  assignments: [
    {
      order_id: "order_abc123xyz",
      porterchain_order_id: "pc-ord-1",
      vehicle_id: "vehicle_abc123xyz",
      driver_id: "driver_abc123xyz",
      sequence: 1,
      distance_m: 4200,
      duration_s: 600,
    },
  ],
  metrics: {
    engine: "vroom",
    assigned_count: 1,
    after_distance_km: 4.2,
    estimated_fuel_cents: 120,
  },
  message: null,
  error: null,
};

async function mockPorterchainBff(page: import("@playwright/test").Page) {
  await page.route("**/api/porterchain/**", async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const path = url.pathname.replace(/^\/api\/porterchain/, "");
    const method = req.method();

    if (path === "/v1/auth/session-context") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(SESSION),
      });
    }

    if (path === "/v1/admin/operations/optimize/pool" && method === "GET") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(POOL),
      });
    }

    if (path === "/v1/admin/operations/optimize/engines" && method === "GET") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ engines: [{ id: "vroom", name: "VROOM" }] }),
      });
    }

    if (path === "/v1/admin/operations/optimize/run" && method === "POST") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ok: true,
          status: "pending",
          run_id: "run-e2e-1",
          assignments: [],
          metrics: { engine: "vroom" },
        }),
      });
    }

    if (path === "/v1/admin/operations/optimize/runs/run-e2e-1" && method === "GET") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(READY),
      });
    }

    if (path === "/v1/admin/operations/optimize/commit" && method === "POST") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ok: true,
          run_id: "run-e2e-1",
          idempotent: false,
          scheduled_date: "2026-09-17",
        }),
      });
    }

    if (path === "/v1/admin/notifications/push-health" && method === "GET") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          tone: "ok",
          issues: [],
          fcm: {
            sdk_available: true,
            credentials_configured: true,
            production_ready: true,
            production_ready_reason: null,
            project_id: "porterchain-test",
            push_enabled: true,
            push_send: true,
            app_env: "local",
          },
          devices: { admin_active: 1, admin_users: 1, driver_active: 0 },
          critical_24h: { total: 0, delivered: 0, failed: 0 },
          last_urgent_push: null,
        }),
      });
    }

    // Control Tower shell polls these — keep quiet with shape-safe empties.
    if (path.startsWith("/v1/admin/operations/") && method === "GET") {
      if (path.endsWith("/stats") || path.includes("/stats?")) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            orders_today: 0,
            revenue_today_cents: 0,
            active_deliveries: 0,
            waiting_dispatch: 0,
            pending_pickups: 0,
            pending_deliveries: 0,
            delayed_orders: 0,
            high_priority_orders: 0,
            failed_deliveries: 0,
            completed_today: 0,
            vehicles_active: 0,
            open_claims: 0,
            support_tickets: 0,
            open_exceptions: 0,
          }),
        });
      }
      if (path.includes("/live-map")) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ drivers: [], orders: [], updated_at: null }),
        });
      }
      if (path.includes("/utilization")) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ vehicles: [], summary: {} }),
        });
      }
      if (path.includes("/sla")) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ at_risk: [], breached: [], ok: [] }),
        });
      }
      if (path.includes("/ai") || path.includes("/copilot")) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ recommendations: [], actions: [] }),
        });
      }
      if (path.includes("/scheduled-batches") || path.includes("/manifests")) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ batches: [], manifests: [], items: [] }),
        });
      }
      // board / queue / orders / assignable-drivers / activity / exceptions / search → arrays
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    }

    if (path.startsWith("/v1/")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({}),
      });
    }

    return route.continue();
  });
}

test.describe(`UI-OPS-006 ${tcId("UI-OPS-006")} @p0`, () => {
  test("Optimize tab: pool → Run preview → Commit", async ({ page }) => {
    test.skip(!process.env.ADMIN_RUN_LIVE, "set ADMIN_RUN_LIVE=1 with admin on :3002 (dev bypass)");

    await ensureAdminReachable(page);
    await mockPorterchainBff(page);
    await page.goto("/operations?view=tools&tool=optimize");
    await expect(page.getByRole("heading", { name: /Operations Control Tower/i })).toBeVisible({
      timeout: 20_000,
    });

    await expect(page.getByRole("button", { name: /^Optimize$/ }).first()).toBeVisible();
    await expect(page.getByText(/Preview orders one assigned van/i)).toBeVisible();
    await expect(page.getByText(/Pool: 2 synced orders ready for orchestrator/i)).toBeVisible();

    await page.getByRole("button", { name: /Run preview/i }).click();
    await expect(page.getByRole("button", { name: /Commit manifests/i })).toBeEnabled({
      timeout: 10_000,
    });
    await expect(
      page
        .locator("select")
        .filter({ has: page.locator('option[value="vroom"]') })
        .first()
    ).toHaveValue("vroom");

    await page.getByRole("button", { name: /Commit manifests/i }).click();
    // After commit, panel clears plan — Commit disabled again / pool still visible.
    await expect(page.getByRole("button", { name: /Commit manifests/i })).toBeDisabled({
      timeout: 10_000,
    });
    await expect(page.getByText(/Pool: 2 synced orders ready for orchestrator/i)).toBeVisible();
  });

  test("Optimize tab shows the PorterChain day plan", async ({ page }) => {
    test.skip(!process.env.ADMIN_RUN_LIVE, "set ADMIN_RUN_LIVE=1 with admin on :3002 (dev bypass)");

    await ensureAdminReachable(page);
    await mockPorterchainBff(page);
    await page.goto("/operations?view=tools&tool=optimize");
    await expect(page.getByText(/Preview orders one assigned van/i)).toBeVisible({
      timeout: 15_000,
    });
    await expect(
      page
        .locator("select")
        .filter({ has: page.locator('option[value="vroom"]') })
        .first()
    ).toHaveValue("vroom");
  });
});
