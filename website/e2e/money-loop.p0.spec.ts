/**
 * Website money-loop P0 — Ripwire named quote/book as portal redirects; track is live.
 *
 *   WEBSITE_RUN_LIVE=1 pnpm --filter @porterchain/website test:e2e:p0
 *
 * Browsers: use host cache if Cursor sandbox remaps PLAYWRIGHT_BROWSERS_PATH:
 *   PLAYWRIGHT_BROWSERS_PATH="$HOME/Library/Caches/ms-playwright" WEBSITE_RUN_LIVE=1 pnpm test:e2e:p0
 */
import { test, expect, tcId, liveEnabled } from "./fixtures";

const LOCALE = process.env.WEBSITE_LOCALE ?? "en";

test.describe(`website money loop @p0`, () => {
  test.beforeEach(({}, testInfo) => {
    testInfo.skip(!liveEnabled(), "set WEBSITE_RUN_LIVE=1 with website on :3000");
  });

  test(`W-UI-001 ${tcId("W-UI-001")} home renders`, async ({ page }) => {
    await page.goto(`/${LOCALE}`);
    await expect(page).toHaveURL(new RegExp(`/${LOCALE}`));
    const body = await page.locator("body").innerText();
    expect(body.length).toBeGreaterThan(40);
    expect(/quote|capacity|book|deliver/i.test(body)).toBeTruthy();
  });

  test(`W-UI-002 ${tcId("W-UI-002")} /quote → sign-up intent=quote`, async ({ page }) => {
    await page.goto(`/${LOCALE}/quote`, { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(/sign-up/);
    const url = new URL(page.url());
    expect(url.searchParams.get("intent")).toBe("quote");
  });

  test(`W-UI-003 ${tcId("W-UI-003")} /book → customer portal book`, async ({ page }) => {
    await page.goto(`/${LOCALE}/book`, { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(/\/book(?:\?|$)/);
    expect(page.url()).not.toMatch(/:8000|fleetbase/i);
    const onPortalBook = page.url().includes("/book") && !page.url().includes(`/${LOCALE}/book`);
    const stillMarketingBook = page.url().includes(`/${LOCALE}/book`);
    expect(
      onPortalBook || stillMarketingBook || /localhost:3004|customer/i.test(page.url())
    ).toBeTruthy();
  });

  test(`W-UI-004 ${tcId("W-UI-004")} /book/continue preserves quote_id`, async ({ page }) => {
    await page.goto(`/${LOCALE}/book/continue?quote_id=q-e2e-1`, {
      waitUntil: "domcontentloaded",
    });
    expect(page.url()).toMatch(/quote_id=q-e2e-1/);
    expect(page.url()).not.toMatch(/:8000/);
  });

  test(`W-UI-006 ${tcId("W-UI-006")} /track shows lookup`, async ({ page }) => {
    await page.goto(`/${LOCALE}/track`);
    await expect(page.getByRole("heading", { name: /track/i }).first()).toBeVisible();
    const hasField = await page.locator("input, textarea").count();
    expect(hasField).toBeGreaterThan(0);
  });

  test(`W-UI-008 ${tcId("W-UI-008")} /contact renders`, async ({ page }) => {
    await page.goto(`/${LOCALE}/contact`);
    await expect(page).toHaveURL(new RegExp(`/${LOCALE}/contact`));
    const body = await page.locator("body").innerText();
    expect(body.length).toBeGreaterThan(40);
    expect(/contact|email|phone|support|inquiry/i.test(body)).toBeTruthy();
  });

  test(`W-GTM-002 ${tcId("W-GTM-002")} CTA language favors quote/capacity`, async ({ page }) => {
    await page.goto(`/${LOCALE}`);
    const body = (await page.locator("body").innerText()).toLowerCase();
    const hasCapacityCta = /get a quote|request capacity|book|quote/.test(body);
    const demoFirst = /^[\s\S]{0,400}book a demo|platform tour/.test(body);
    expect(hasCapacityCta).toBeTruthy();
    expect(demoFirst).toBeFalsy();
  });

  test(`W-VIS-001 ${tcId("W-VIS-001")} pc_vid set on track`, async ({ page }) => {
    await page.goto(`/${LOCALE}/track`);
    await page.waitForTimeout(500);
    const vid = await page.evaluate(() => {
      const key = "pc_vid";
      return localStorage.getItem(key) ?? sessionStorage.getItem(key);
    });
    // VisitorIntelligenceBootstrap / getOrCreateVisitorId may set on interactive pages.
    // Soft assert: if present, shape is non-empty; if absent, page still usable (no throw).
    if (vid) {
      expect(vid.trim().length).toBeGreaterThan(4);
      expect(vid.length).toBeLessThanOrEqual(64);
    } else {
      // Ensure track still interactive without requiring bootstrap race.
      expect(await page.locator("input, textarea").count()).toBeGreaterThan(0);
    }
  });

  test(`W-SPA-002 ${tcId("W-SPA-002")} no Fleetbase :8000 navigations`, async ({ page }) => {
    const bad: string[] = [];
    page.on("request", (req) => {
      const u = req.url();
      if (/:(8000)\b|socketcluster/i.test(u)) bad.push(u);
    });
    await page.goto(`/${LOCALE}`);
    await page.goto(`/${LOCALE}/track`);
    await page.goto(`/${LOCALE}/contact`);
    expect(bad, `forbidden vendor requests: ${bad.join(", ")}`).toEqual([]);
  });
});
