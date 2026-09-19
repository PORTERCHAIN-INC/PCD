import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.DRIVER_BASE_URL ?? "http://localhost:3003";

/**
 * Driver portal P0 e2e — skeletons tagged with SSOT IDs from
 * docs/testing/driver_p0_registry.json / docs/DRIVER_ADMIN_DEV_TEST_CASES.md
 *
 * Run: pnpm --filter @porterchain/driver-portal test:e2e:p0
 * Needs: driver-portal on :3003 + session (see e2e/fixtures.ts).
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    storageState: process.env.DRIVER_STORAGE_STATE || undefined,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
