import { defineConfig, devices } from "@playwright/test";
import { adminBaseUrl, resolveStaffStorageState } from "./e2e/fixtures";

const baseURL = adminBaseUrl();

/**
 * Admin portal P0 e2e — skeletons tagged with SSOT IDs from
 * docs/testing/admin_p0_registry.json / docs/ADMIN_SUPERADMIN_DEV_TESTCASES.md
 *
 * Run: pnpm --filter @porterchain/admin test:e2e:p0
 * Auth: ADMIN_STORAGE_STATE | ADMIN_STAFF_SID | empty + NEXT_PUBLIC_CLERK_DEV_BYPASS
 * Live: ADMIN_RUN_LIVE=1 (hard-fail if portal down)
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  use: {
    baseURL,
    storageState: resolveStaffStorageState(),
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  // Opt-in only — `pnpm exec` can re-install and race the monorepo. Prefer a
  // separately started admin (`NEXT_PUBLIC_CLERK_DEV_BYPASS=true pnpm --filter @porterchain/admin dev`).
  ...(process.env.ADMIN_E2E_WEBSERVER === "1"
    ? {
        webServer: {
          command: `NEXT_PUBLIC_CLERK_DEV_BYPASS=true npx next dev -H 127.0.0.1 -p ${new URL(baseURL).port || "3002"}`,
          url: baseURL,
          reuseExistingServer: true,
          timeout: 120_000,
        },
      }
    : {}),
});
