import { test, expect, playwrightCases, tcId } from "./fixtures";

/**
 * AUTH + onboarding gate wiring.
 * No browser launch — flip to live asserts when registry status=implemented.
 */
const authCases = playwrightCases("skeleton").filter((c) => ["UI-D-01", "UI-D-10"].includes(c.id));

for (const c of authCases) {
  test.describe(`${c.id} ${tcId(c.id)} @p0`, () => {
    test(c.title, () => {
      expect(["UI-D-01", "UI-D-10"]).toContain(c.id);
      expect(c.title.length).toBeGreaterThan(0);
    });
  });
}

test.describe(`UI-D-01 ${tcId("UI-D-01")} smoke-when-ready`, () => {
  test("unauthenticated /dashboard redirects to login", async ({ page }) => {
    test.skip(
      !process.env.DRIVER_RUN_LIVE || !!process.env.DRIVER_STORAGE_STATE,
      "set DRIVER_RUN_LIVE=1 without storage"
    );
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/login|sign-in|onboarding/);
  });
});
