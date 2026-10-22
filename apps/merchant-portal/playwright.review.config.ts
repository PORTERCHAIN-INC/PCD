import { defineConfig, devices } from "@playwright/test";

/**
 * Shopify App Review entry paths, against a preview or production (read-only except
 * the optional self sign-up, which creates one test merchant).
 *
 *   REVIEW_E2E_LIVE=1 MERCHANT_BASE_URL=https://merchant.porterchain.com \
 *   REVIEW_EMAIL=... REVIEW_PASSWORD=... \
 *   [REVIEW_SIGNUP_EMAIL=you+tag@gmail.com REVIEW_CODE_FILE=/tmp/code.txt] \
 *   pnpm exec playwright test -c playwright.review.config.ts
 *
 * Email codes: the test waits for REVIEW_CODE_FILE to contain the 6-digit code.
 * Every run records video (test-results/), fresh profile, third-party cookies blocked.
 */
const baseURL = process.env.MERCHANT_BASE_URL ?? "https://merchant.porterchain.com";

export default defineConfig({
  testDir: "./e2e-review",
  timeout: 240_000,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: { baseURL, video: "on", trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [
    {
      name: "chrome-3pc-blocked",
      use: {
        // No device preset: its fixed user agent mismatches the real browser and trips the human check.
        viewport: { width: 1280, height: 800 },
        // A reviewer's real Chrome: Cloudflare's human check refuses obvious automation.
        launchOptions: {
          executablePath: process.env.REVIEW_CHROME_PATH || undefined,
          ignoreDefaultArgs: ["--enable-automation"],
          args: [
            "--test-third-party-cookie-phaseout",
            "--disable-blink-features=AutomationControlled",
          ],
        },
      },
    },
    // WebKit blocks third-party cookies by default (Safari ITP behaviour).
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
  ],
});
