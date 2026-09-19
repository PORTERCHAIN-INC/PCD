import { test, expect, playwrightCases, tcId } from "./fixtures";

/**
 * AUTH + top-route P0 wiring.
 * Live browser asserts unlock with ADMIN_RUN_LIVE=1 after `pnpm test:e2e:install`.
 */
const authAndNav = playwrightCases("skeleton").filter((c) =>
  ["AUTH-001", "AUTH-007", "UI-DASH-001", "UX-007"].includes(c.id)
);

for (const c of authAndNav) {
  test.describe(`${c.id} ${tcId(c.id)} @p0`, () => {
    test(c.title, () => {
      expect(c.id.length).toBeGreaterThan(0);
      expect(c.title.length).toBeGreaterThan(0);
      expect(["BOTH", "SA", "AD", "NEG", "SKIP"]).toContain(c.persona);
    });
  });
}

test.describe(`AUTH-001 ${tcId("AUTH-001")} smoke-when-ready`, () => {
  // Empty jar — must not inherit ADMIN_STORAGE_STATE / ADMIN_STAFF_SID from config.
  test.use({ storageState: { cookies: [], origins: [] } });

  test("unauthenticated /dashboard redirects to sign-in", async ({ page }) => {
    test.skip(
      !process.env.ADMIN_RUN_LIVE ||
        !!process.env.ADMIN_STORAGE_STATE ||
        !!process.env.ADMIN_STAFF_SID ||
        process.env.NEXT_PUBLIC_CLERK_DEV_BYPASS === "true",
      "set ADMIN_RUN_LIVE=1 without storage/sid/bypass (and playwright install chromium)"
    );
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/sign-in/);
  });
});
