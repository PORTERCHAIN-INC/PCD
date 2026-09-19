import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.MERCHANT_BASE_URL ?? "http://localhost:3001";

/**
 * Merchant portal P0 e2e.
 *
 * Default CI: contracts + skeletons (no browser auth).
 * Golden live slice:
 *   MERCHANT_E2E_LIVE=1 \
 *   MERCHANT_STORAGE_STATE_DISPATCHER=e2e/.auth/dispatcher.json \
 *   MERCHANT_STORAGE_STATE_VIEWER=e2e/.auth/viewer.json \
 *   pnpm test:e2e:p0 --grep 'MP-BOOK-001|MP-AUTH-006'
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
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
