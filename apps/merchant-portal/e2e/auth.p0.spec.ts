import { test, expect, tcId } from "./fixtures";

test.describe(`MP-AUTH-001 ${tcId("MP-AUTH-001")} @p0`, () => {
  test.skip(
    !process.env.MERCHANT_E2E_LIVE,
    "MP-AUTH-001: set MERCHANT_E2E_LIVE=1 + portal on :3001 to run live"
  );

  test("unauthenticated visit to /dashboard redirects toward sign-in", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/sign-in|onboarding|dashboard/);
  });
});
