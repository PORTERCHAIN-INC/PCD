/**
 * Footer, motion fallback, track, industry merges, area selector (Oct 2026 round).
 */
import { test, expect } from "./fixtures";

test.describe("footer @website", () => {
  test("one contentinfo landmark, five groups, contact, hours, coverage, Shopify badge", async ({
    page,
  }) => {
    await page.goto("/en");
    const footer = page.getByRole("contentinfo");
    await expect(footer).toHaveCount(1);
    for (const h of ["Services", "Industries", "Company", "Support", "Legal"]) {
      await expect(footer.getByRole("heading", { name: h, exact: true })).toBeVisible();
    }
    await expect(footer.getByTestId("footer-hours")).toContainText("Mon–Fri 8 AM–6 PM");
    await expect(footer.getByTestId("footer-hours")).toContainText("Sat 9 AM–2 PM");
    await expect(footer.getByTestId("footer-coverage")).toContainText("362 postal areas");
    await expect(footer.getByTestId("footer-shopify-badge")).toBeVisible();
    await expect(footer.locator('a[href^="tel:"]')).toHaveCount(1);
    await expect(footer.locator('a[href^="mailto:"]')).toHaveCount(1);
    const hrefs = await footer
      .locator("nav a")
      .evaluateAll((as) => as.map((a) => a.getAttribute("href")));
    expect(new Set(hrefs).size).toBe(hrefs.length);
    for (const gone of [
      "/en/capabilities",
      "/en/solutions",
      "/en/how-porterchain-works",
      "/en/integrations-education",
    ]) {
      expect(hrefs.some((h) => h?.startsWith(gone))).toBe(false);
    }
  });
});

test.describe("motion @website", () => {
  test("tracking demo animates, and stays still with reduced motion", async ({ browser }) => {
    for (const reducedMotion of ["no-preference", "reduce"] as const) {
      const ctx = await browser.newContext({ reducedMotion });
      const page = await ctx.newPage();
      await page.goto("/en");
      const box = page.getByTestId("tracking-motion");
      const before = await box.boundingBox();
      await box.scrollIntoViewIfNeeded();
      await expect(box).toHaveAttribute(
        "data-motion",
        reducedMotion === "reduce" ? "still" : "motion",
        { timeout: 15000 }
      );
      const after = await box.boundingBox();
      expect(Math.round(after!.height)).toBe(Math.round(before!.height)); // no layout shift
      await ctx.close();
    }
  });
  test("no walking-person animation is shipped", async ({ request }) => {
    expect((await request.get("/lottie/shipment.json")).status()).toBe(404);
  });
});

test.describe("track @website", () => {
  test("entry is one input, no hero photo, routes to the result", async ({ page }) => {
    await page.goto("/en/track");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Track a delivery");
    const form = page.getByTestId("track-form");
    await expect(form.locator("input")).toHaveCount(1);
    await expect(page.locator("main img")).toHaveCount(0);
    await form.locator("input").fill("pc-nope123");
    await form.locator("button").click();
    await expect(page).toHaveURL(/\/en\/track\/PC-NOPE123$/);
    await expect(page.locator("main").getByRole("alert")).toContainText("not found");
  });
});

test.describe("industries @website", () => {
  test("five hubs, merged hubs 301 once", async ({ request }) => {
    for (const [from, to] of [
      ["/en/delivery/labs", "/en/delivery/pharmacy"],
      ["/en/delivery/plumbing-electrical/vaughan", "/en/delivery/construction/vaughan"],
      ["/en/delivery/wholesale-traders", "/en/delivery/warehouses"],
    ]) {
      const res = await request.get(from, { maxRedirects: 0 });
      expect(res.status(), from).toBe(301);
      expect(new URL(res.headers().location!, "http://x").pathname).toBe(to);
    }
  });
  test("area selector links are real anchors in the server HTML; one services strip; contact bar", async ({
    request,
    page,
  }) => {
    const html = await (await request.get("/en/delivery/pharmacy/mississauga")).text();
    expect(html.match(/href="\/en\/delivery\/pharmacy\/[a-z-]+"/g)?.length ?? 0).toBeGreaterThan(
      10
    );
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/en/delivery/pharmacy/mississauga");
    await expect(page.getByTestId("services-strip")).toHaveCount(1);
    await expect(page.getByTestId("contact-bar")).toContainText("+1 (647) 619-7951");
    const selector = page.getByTestId("area-selector");
    await expect(selector.getByRole("link", { name: "Brampton" })).toBeHidden(); // collapsed on mobile
    await selector.getByRole("searchbox").fill("bramp");
    await expect(selector.getByRole("link", { name: "Brampton" })).toBeVisible();
    await expect(selector.getByRole("link", { name: "Markham" })).toBeHidden();
  });
});

test.describe("blog @website", () => {
  test("unknown slug is a real 404", async ({ request }) => {
    expect((await request.get("/en/blog/definitely-not-a-post-xyz")).status()).toBe(404);
  });
});

test.describe("thin pages filled or merged (Oct 2026)", () => {
  test("unknown URL renders the designed 404 with real links and a footer", async ({ page }) => {
    const res = await page.goto("/en/this-page-does-not-exist");
    expect(res?.status()).toBe(404);
    await expect(page.getByRole("heading", { level: 1 })).toContainText(/moved or never existed/i);
    await expect(page.locator("main a[href='/en/delivery-cost-calculator']")).toBeVisible();
    await expect(page.getByTestId("footer-coverage")).toBeVisible();
  });

  for (const [from, to] of [
    ["/en/success-stories", "/en/delivery"],
    ["/en/success-stories/pharmacy-patient-delivery", "/en/delivery/pharmacy"],
    ["/en/local-delivery", "/en/service-areas"],
  ] as const) {
    test(`${from} → ${to} in one 301`, async ({ request }) => {
      const res = await request.get(from, { maxRedirects: 0 });
      expect(res.status()).toBe(301);
      expect(new URL(res.headers().location!, "http://x").pathname).toBe(to);
    });
  }

  test("/vehicles lists the three bookable classes with capacities", async ({ page }) => {
    await page.goto("/en/vehicles");
    const table = page.getByRole("table");
    for (const v of ["Sedan / SUV", "Cargo van", "16 ft box truck"])
      await expect(table).toContainText(v);
  });
});
