import { existsSync, readFileSync, rmSync } from "node:fs";
import { expect, test, type Page } from "@playwright/test";

const LIVE = process.env.REVIEW_E2E_LIVE === "1";
const CODE_FILE = process.env.REVIEW_CODE_FILE ?? "";
const FEATURES = ["/dashboard", "/book", "/orders", "/billing", "/settings", "/shopify"];

test.skip(!LIVE, "set REVIEW_E2E_LIVE=1 to run against a deployed portal");

async function waitForCode(): Promise<string> {
  if (!CODE_FILE) throw new Error("email code requested: set REVIEW_CODE_FILE");
  for (let i = 0; i < 90; i++) {
    if (existsSync(CODE_FILE)) {
      const code = readFileSync(CODE_FILE, "utf8").trim();
      rmSync(CODE_FILE);
      if (/^\d{6}$/.test(code)) return code;
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
  throw new Error("no email code arrived");
}

/** Clerk's Cloudflare check can ask for a click ("Verify you are human"), as a reviewer would. */
async function passHumanCheckIfShown(page: Page) {
  const frame = page.frameLocator('iframe[src*="challenges.cloudflare.com"]');
  const box = frame.locator('input[type="checkbox"], label').first();
  if (await box.isVisible({ timeout: 10_000 }).catch(() => false)) await box.click();
}

async function enterCodeIfAsked(page: Page) {
  const code = page.locator('input[name="code"], input[autocomplete="one-time-code"]').first();
  if (await code.isVisible({ timeout: 8000 }).catch(() => false)) {
    await code.click();
    await page.keyboard.type(await waitForCode());
  }
}

async function expectFullFeatures(page: Page) {
  await page.waitForURL((u) => !/sign-(in|up)|verify/.test(u.pathname), { timeout: 60_000 });
  for (const path of FEATURES) {
    await page.goto(path);
    await expect(page).not.toHaveURL(/sign-in|onboarding/);
    await expect(page.getByText("This page could not be found")).toHaveCount(0);
    await expect(page.getByText(/awaiting approval|pending approval/i)).toHaveCount(0);
  }
}

test("review account signs in with email + password and reaches every feature", async ({
  page,
}) => {
  test.skip(
    !process.env.REVIEW_EMAIL || !process.env.REVIEW_PASSWORD,
    "review credentials not set"
  );
  await page.goto("/sign-in");
  await page.fill('input[name="identifier"]', process.env.REVIEW_EMAIL ?? "");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.fill('input[name="password"]', process.env.REVIEW_PASSWORD ?? "");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await enterCodeIfAsked(page); // Clerk new-device check, when enabled
  await expectFullFeatures(page);
});

test("brand-new self sign-up → email code → merchant → full features", async ({ page }) => {
  const email = process.env.REVIEW_SIGNUP_EMAIL;
  test.skip(!email, "REVIEW_SIGNUP_EMAIL not set (creates a real test merchant)");
  await page.goto("/sign-up");
  await page.fill('input[name="emailAddress"]', email ?? "");
  await page.fill('input[name="password"]', `Rv-${Date.now()}-x9!Q`);
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await passHumanCheckIfShown(page);
  await page.waitForURL(/verify/, { timeout: 60_000 });
  await enterCodeIfAsked(page);
  await expectFullFeatures(page);
});

test("Clerk blocked → clear error with retry, never an endless spinner", async ({ page }) => {
  await page.route(/clerk\.(admin\.)?porterchain\.com|clerk\.accounts\.dev|clerk-js/, (r) =>
    r.abort()
  );
  await page.goto("/sign-in");
  await expect(page.getByTestId("auth-load-failed")).toBeVisible({ timeout: 25_000 });
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
});

test("Google sign-in stays optional next to email + password", async ({ page }) => {
  await page.goto("/sign-in");
  await expect(page.locator('input[name="identifier"]')).toBeVisible({ timeout: 30_000 });
});

test("embedded app page loads outside Shopify without a login wall", async ({ page }) => {
  const res = await page.goto("/shopify-app");
  expect(res?.status()).toBeLessThan(500);
  await expect(page).not.toHaveURL(/sign-in/);
});
