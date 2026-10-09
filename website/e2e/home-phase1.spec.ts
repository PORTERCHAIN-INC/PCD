/**
 * Website Phase 1 — homepage calculator flow, navigation, sticky mobile price bar.
 *
 *   WEBSITE_RUN_LIVE=1 pnpm --filter @porterchain/website test:e2e -- home-phase1
 *
 * Calculator tests mock /api/estimate (deterministic) except the "live local API" case, which
 * prices a trip through the running local API and checks the page shows the same amount.
 * No lead is ever submitted.
 */
import { test, expect, liveEnabled } from "./fixtures";
import type { Page } from "@playwright/test";

const SAMPLE = {
  amount_cents: 13560,
  subtotal_cents: 12000,
  tax_cents: 1560,
  distance_km: 21.4,
  vehicle_class: "cargo_van",
  pickup_fsa: "M5V",
  dropoff_fsa: "L4W",
  lines: [],
  disclaimer: "Estimate for testing.",
};

async function mockEstimate(page: Page, status = 200, body: object = SAMPLE) {
  const requests: Array<Record<string, string>> = [];
  await page.route("**/api/estimate", async (route) => {
    requests.push(route.request().postDataJSON());
    await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
  });
  return requests;
}

const form = (page: Page) => page.getByTestId("home-price-form");

test.describe("homepage calculator @phase1", () => {
  test.beforeEach(({}, testInfo) => {
    testInfo.skip(!liveEnabled(), "set WEBSITE_RUN_LIVE=1 with website on :3000");
  });

  test("prices a trip and hands off to booking + full breakdown", async ({ page }) => {
    const requests = await mockEstimate(page);
    await page.goto("/en");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      /same-day delivery across the gta/i
    );
    await form(page).getByLabel("Pickup postal code").fill("m5v 2t6");
    await form(page).getByLabel("Drop-off postal code").fill("L4W 1N7");
    await form(page).getByText("Cargo van", { exact: true }).click();
    await form(page)
      .getByRole("button", { name: /get a price/i })
      .click();

    const result = page.getByTestId("home-price-result");
    await expect(result).toContainText("$135.60");
    await expect(result).toContainText("M5V → L4W · Cargo van");
    expect(requests).toEqual([
      { pickup_postal: "M5V", dropoff_postal: "L4W", vehicle_class: "cargo_van" },
    ]);

    const book = result.getByRole("link", { name: /book this delivery/i });
    await expect(book).toHaveAttribute("href", /\/sign-up\?.*intent=quote/);
    await expect(book).toHaveAttribute("href", /vehicle=cargo_van/);
    const details = result.getByRole("link", { name: /see full breakdown/i });
    await expect(details).toHaveAttribute(
      "href",
      /\/delivery-cost-calculator\?pickup=M5V&dropoff=L4W&vehicle=cargo_van/
    );
  });

  test("validates postal codes before calling the API", async ({ page }) => {
    const requests = await mockEstimate(page);
    await page.goto("/en");
    await form(page).getByLabel("Pickup postal code").fill("12345");
    await form(page)
      .getByRole("button", { name: /get a price/i })
      .click();
    await expect(page.locator("#home-price").getByRole("alert")).toContainText(
      /valid postal code/i
    );
    expect(requests).toHaveLength(0);
  });

  test("explains an out-of-area postal code", async ({ page }) => {
    await mockEstimate(page, 422, { error: "dropoff_outside_service_area" });
    await page.goto("/en");
    await form(page).getByLabel("Pickup postal code").fill("M5V");
    await form(page).getByLabel("Drop-off postal code").fill("K1A 0B1");
    await form(page)
      .getByRole("button", { name: /get a price/i })
      .click();
    await expect(page.locator("#home-price").getByRole("alert")).toContainText(
      /outside our GTA coverage/i
    );
  });

  test("French homepage prices in fr-CA format", async ({ page }) => {
    await mockEstimate(page);
    await page.goto("/fr");
    await form(page).getByLabel("Code postal de ramassage").fill("M5V");
    await form(page).getByLabel("Code postal de livraison").fill("L4W");
    await form(page)
      .getByRole("button", { name: /obtenir un prix/i })
      .click();
    await expect(page.getByTestId("home-price-result")).toContainText(/135,60\s\$/);
  });

  test("live local API: page shows the same price as /api/estimate", async ({ page, request }) => {
    const direct = await request.post("/api/estimate", {
      data: { pickup_postal: "M5V", dropoff_postal: "L4W", vehicle_class: "sedan_suv" },
    });
    test.skip(!direct.ok(), `estimate API not available locally (${direct.status()})`);
    const expected = (await direct.json()).amount_cents as number;
    await page.goto("/en");
    await form(page).getByLabel("Pickup postal code").fill("M5V");
    await form(page).getByLabel("Drop-off postal code").fill("L4W");
    await form(page).getByText("Sedan / SUV", { exact: true }).click();
    await form(page)
      .getByRole("button", { name: /get a price/i })
      .click();
    await expect(page.getByTestId("home-price-result")).toContainText(
      `$${(expected / 100).toFixed(2)}`
    );
  });

  test("FAQ schema, sample tracking label and real-data trust strip", async ({ page }) => {
    await page.goto("/en");
    const schemas = await page.locator('script[type="application/ld+json"]').allTextContents();
    const faq = schemas
      .map((s) => JSON.parse(s))
      .flat()
      .find((s) => s["@type"] === "FAQPage");
    expect(faq?.mainEntity?.length).toBe(6); // top 6 of the core FAQ (data/faq-core.ts)
    const sample = page.getByTestId("tracking-sample");
    await expect(sample).toContainText("Sample");
    await expect(sample).toContainText(/not a real order/i);
    await expect(page.getByText(/^\d+ postal areas$/)).toBeVisible();
  });
});

test.describe("navigation @phase1", () => {
  test.beforeEach(({}, testInfo) => {
    testInfo.skip(!liveEnabled(), "set WEBSITE_RUN_LIVE=1 with website on :3000");
  });

  const TOP = [
    ["Price", "/en/delivery-cost-calculator"],
    ["Industries", "/en/delivery"],
    ["Track", "/en/track"],
    ["Shopify app", "/en/delivery/shopify-merchants"],
    ["Sign in", "/en/login"],
  ] as const;

  test("desktop header has the five top links, all resolving", async ({ page, request }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/en/track");
    const nav = page.getByRole("banner").getByRole("navigation", { name: "Primary" });
    const links = nav.getByRole("link");
    await expect(links).toHaveCount(TOP.length);
    for (const [index, [name, href]] of TOP.entries()) {
      await expect(links.nth(index)).toHaveText(name);
      await expect(links.nth(index)).toHaveAttribute("href", href);
      const res = await request.get(href, { maxRedirects: 0 });
      expect(res.status(), href).toBe(200);
    }
    await expect(nav.getByRole("link", { name: "Track" })).toHaveAttribute("aria-current", "page");
    await expect(page.getByRole("banner").getByRole("link", { name: "Book now" })).toBeVisible();
  });

  test("old nav destinations stay reachable from the footer", async ({ page }) => {
    await page.goto("/en");
    const footer = page.getByRole("contentinfo");
    await expect(footer.locator('a[href="/en/business"]')).toHaveCount(1);
    await expect(footer.locator('a[href="/en/vehicle-partner"]')).toHaveCount(1);
  });

  test("mobile menu lists the same links and closes on Escape", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/en/track");
    const toggle = page.getByRole("button", { name: /toggle navigation menu/i });
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    const sheet = page.locator("#site-mobile-menu");
    for (const [name] of TOP) {
      await expect(sheet.getByRole("link", { name, exact: true })).toBeVisible();
    }
    await page.keyboard.press("Escape");
    await expect(sheet).toHaveCount(0);
  });

  test("sticky mobile 'Get a price' bar returns to the hero calculator", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    // A returning visitor: consent already chosen, so the cookie banner is not covering the bar.
    await page.addInitScript(() =>
      localStorage.setItem(
        "pc_cookie_consent_v1",
        JSON.stringify({ necessary: true, analytics: false, marketing: false, functional: false })
      )
    );
    await page.goto("/en");
    const bar = page.locator(".price-bar");
    await expect(bar).not.toHaveClass(/price-bar--on/);
    await page.mouse.wheel(0, 1800);
    await expect(bar).toHaveClass(/price-bar--on/);
    await bar.getByRole("link", { name: /get a price/i }).click();
    await expect(page.locator("#home-price")).toBeInViewport();
    await expect(bar).not.toHaveClass(/price-bar--on/);
  });
});
