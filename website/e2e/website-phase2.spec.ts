/**
 * Website Phase 1 decisions + design pass — approved promise, 362-area coverage, furniture hub,
 * calculator page, factual trust badges, hidden reviews / case study.
 *
 *   WEBSITE_RUN_LIVE=1 pnpm --filter @porterchain/website test:e2e -- website-phase2
 *
 * Read-only: no form is submitted and no lead is created.
 */
import { test, expect, liveEnabled } from "./fixtures";

type Schema = Record<string, unknown> & { "@type"?: string };

async function schemas(page: import("@playwright/test").Page): Promise<Schema[]> {
  const raw = await page.locator('script[type="application/ld+json"]').allTextContents();
  return raw.flatMap((s) => {
    const parsed = JSON.parse(s);
    const list = Array.isArray(parsed) ? parsed : [parsed];
    return list.flatMap((item: Schema) =>
      Array.isArray(item["@graph"]) ? (item["@graph"] as Schema[]) : [item]
    );
  });
}

test.describe("website phase 2 @phase1", () => {
  test.beforeEach(({}, testInfo) => {
    testInfo.skip(!liveEnabled(), "set WEBSITE_RUN_LIVE=1 with website on :3000");
  });

  test("home shows the approved promise, factual badges and no fake proof", async ({ page }) => {
    await page.goto("/en");
    await expect(page.getByTestId("home-promise")).toHaveText(
      /Order by 11 AM\. Delivered 2–9 PM same day, Mon–Sat\./
    );
    await expect(page.getByText(/needs sign-off/i)).toHaveCount(0);
    const badges = page.getByRole("list", { name: "Included with every delivery" }).first();
    await expect(badges).toContainText("Live tracking");
    await expect(badges).toContainText("Photo proof of delivery");
    // Reviews and the Kaylulu case study stay hidden until permission/real reviews exist.
    await expect(page.getByText(/kaylulu/i)).toHaveCount(0);
    await expect(page.locator('[itemprop="review"], [data-testid="reviews-proof"]')).toHaveCount(0);
    // Furniture tile points at the new industry hub.
    await expect(page.locator('main a[href="/en/delivery/furniture"]').first()).toBeVisible();
    // Comparison block + final CTA band.
    await expect(
      page.getByRole("heading", { name: /what every delivery includes/i })
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: /price your next delivery/i })).toBeVisible();
    await expect(page.getByText(/^362 postal areas$/)).toBeVisible();
  });

  test("French home renders the promise in French", async ({ page }) => {
    await page.goto("/fr");
    await expect(page.getByTestId("home-promise")).toContainText(/11 h/);
    await expect(page.getByTestId("home-promise")).toContainText(/lundi au samedi/);
  });

  test("furniture hub: service details, limits, FAQ + Service schema", async ({
    page,
    request,
  }) => {
    const res = await request.get("/en/delivery/furniture", { maxRedirects: 0 });
    expect(res.status()).toBe(200);
    await page.goto("/en/delivery/furniture");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(/furniture/i);
    const body = page.locator("main");
    await expect(body).toContainText(/16 ft box truck/i);
    await expect(body).toContainText(/threshold/i);
    await expect(body).toContainText(/50 lb \(23 kg\)/);
    await expect(body).toContainText(/liftgate/i);
    await expect(body).toContainText(/assembly/i);
    await expect(body).toContainText("362 FSAs");
    const all = await schemas(page);
    const faq = all.find((s) => s["@type"] === "FAQPage") as { mainEntity?: unknown[] } | undefined;
    expect(faq?.mainEntity?.length).toBe(8);
    expect(all.some((s) => s["@type"] === "Service")).toBe(true);
    // Area pages link out and resolve; the thin Milton page is not linked.
    await expect(page.locator('a[href="/en/delivery/furniture/milton"]')).toHaveCount(0);
    const area = await request.get("/en/delivery/furniture/mississauga", { maxRedirects: 0 });
    expect(area.status()).toBe(200);
  });

  test("legacy furniture URLs 301 once to the furniture hub", async ({ request }) => {
    for (const from of [
      "/industries/furniture-delivery",
      "/en/industries/furniture-delivery",
      "/fr/industries/furniture-delivery",
      "/en/solutions/furniture",
    ]) {
      const res = await request.get(from, { maxRedirects: 0 });
      expect(res.status(), from).toBe(301);
      const location = new URL(res.headers()["location"] ?? "", "http://x").pathname;
      expect(location, from).toBe("/en/delivery/furniture");
      const next = await request.get(location, { maxRedirects: 0 });
      expect(next.status(), location).toBe(200);
    }
  });

  test("delivery index and sitemap include the furniture hub", async ({ page, request }) => {
    await page.goto("/en/delivery");
    await expect(page.locator('main a[href="/en/delivery/furniture"]').first()).toBeVisible();
    const llms = await (await request.get("/llms.txt")).text();
    expect(llms).toContain("362 postal areas");
    expect(llms).toContain("/en/delivery/furniture");
  });

  test("calculator page: hero, live calculator and price explainer", async ({ page }) => {
    await page.goto("/en/delivery-cost-calculator");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(/calculator/i);
    await expect(page.getByRole("heading", { name: /how the price is built/i })).toBeVisible();
    await expect(page.getByLabel(/pickup postal code/i).first()).toBeVisible();
    await expect(page.locator("main")).toContainText("362 FSAs");
  });

  test("facts page states 362 postal areas", async ({ page }) => {
    await page.goto("/en/facts");
    await expect(page.locator("main")).toContainText("362");
    await expect(page.locator("main")).not.toContainText(/\b357\b/);
  });
});
