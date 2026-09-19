import fs from "fs";
import os from "os";
import path from "path";
import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.WEBSITE_BASE_URL ?? "http://localhost:3000";

/**
 * Prefer an explicit binary (arm64 host cache) when Cursor/agent runners
 * mis-resolve Playwright's platform as mac-x64.
 */
function resolveChromiumExecutable(): string | undefined {
  if (process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH) {
    return process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH;
  }
  const home = process.env.HOME || os.homedir();
  const cache =
    process.env.PLAYWRIGHT_BROWSERS_PATH || path.join(home, "Library/Caches/ms-playwright");
  const candidates = [
    path.join(
      cache,
      "chromium-1243/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
    ),
    path.join(
      cache,
      "chromium_headless_shell-1243/chrome-headless-shell-mac-arm64/chrome-headless-shell"
    ),
  ];
  return candidates.find((p) => fs.existsSync(p));
}

const chromiumExecutable = resolveChromiumExecutable();

/**
 * Website P0 e2e — money loop + redirect contracts.
 * SSOT: docs/WEBSITE_PERSONA_DEV_TEST_CASES.md · docs/RIPWIRE_QUOTE_VISITOR_OPTIMIZE.md
 * Registry: docs/testing/website_p0_registry.json
 *
 *   pnpm --filter @porterchain/website test:e2e:install
 *   WEBSITE_RUN_LIVE=1 pnpm --filter @porterchain/website test:e2e:p0
 *
 * Needs: website on :3000 (next dev). No Fleetbase. Book UX is on customer :3004.
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
    ...(chromiumExecutable ? { launchOptions: { executablePath: chromiumExecutable } } : {}),
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
