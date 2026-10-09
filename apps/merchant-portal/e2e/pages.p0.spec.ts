import {
  test,
  expect,
  playwrightCases,
  tcId,
  liveReady,
  liveSkipReason,
  storageStatePath,
} from "./fixtures";

/** Page / subpage P0 skeletons — one describe per SSOT id. */
const pageCases = playwrightCases("skeleton").filter(
  (c) => c.id.startsWith("MP-") || c.id.startsWith("AD-")
);

const ROUTE_HINT: Record<string, string> = {
  "MP-AUTH-001": "/sign-in",
  "MP-AUTH-006": "/book",
  "MP-ONB-001": "/onboarding",
  "MP-DASH-001": "/dashboard",
  "MP-BOOK-001": "/book",
  "MP-RTE-001": "/routes",
  "MP-ORD-001": "/orders",
  "MP-TRK-001": "/track",
  "MP-BIL-001": "/billing",
  "MP-INT-001": "/api",
  "MP-SHP-001": "/shopify",
  "MP-SET-001": "/settings",
  "MP-NTF-001": "/notifications",
  "MP-REF-001": "/referrals",
  "AD-LIST-001": "/merchants",
  "AD-360-001": "/merchants",
  "AD-360-006": "/merchants",
  "AD-360-007": "/merchants",
};

for (const c of pageCases) {
  // Admin AD-* cases run against admin portal — skip in merchant package.
  if (c.id.startsWith("AD-")) continue;

  test.describe(`${c.id} ${tcId(c.id)} @p0`, () => {
    test.skip(!liveReady("dispatcher"), liveSkipReason("dispatcher"));
    const jar = storageStatePath("dispatcher");
    if (jar) test.use({ storageState: jar });

    test(c.title, async ({ page }) => {
      const route = ROUTE_HINT[c.id] ?? "/dashboard";
      const errors: string[] = [];
      page.on("pageerror", (err) => errors.push(err.message));
      const res = await page.goto(route);
      expect(res?.status() ?? 200, `${route} HTTP status`).toBeLessThan(400);
      await page.waitForLoadState("networkidle").catch(() => undefined);
      await expect(page.locator("body")).not.toContainText(/This page could not be found/i);
      await expect(page.locator("body")).not.toContainText(
        /Application error|Something went wrong/i
      );
      await expect(page.locator("main, [role=main]").first()).toBeVisible({ timeout: 15_000 });
      expect(errors, `uncaught errors on ${route}`).toEqual([]);
    });
  });
}
