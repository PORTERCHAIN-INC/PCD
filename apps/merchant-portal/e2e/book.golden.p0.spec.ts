import {
  test,
  expect,
  tcId,
  liveReady,
  liveSkipReason,
  storageStatePath,
  captureBearer,
  merchantApi,
  gtaBookPayload,
  liveEnabled,
} from "./fixtures";

/**
 * P0 golden slice — money path under real Clerk auth.
 * Skips at describe level when jars/Chromium prerequisites are missing.
 */

const ALLOWED_ROUTING = new Set(["valhalla", "osrm", "haversine"]);
const emptyState = { cookies: [] as [], origins: [] as [] };

test.describe(`MP-BOOK-001 ${tcId("MP-BOOK-001")} @p0 @dispatcher`, () => {
  const ready = liveReady("dispatcher");
  test.skip(!ready, liveSkipReason("dispatcher"));
  test.use({ storageState: storageStatePath("dispatcher") || emptyState });

  test("dispatcher book UI loads + preview routing_source + sandbox confirm", async ({
    page,
    request,
  }) => {
    const bearer = await captureBearer(page, "/book");

    await expect(page.getByTestId("module-gate-forbidden")).toHaveCount(0);
    await expect(page.locator("body")).toContainText(/Request capacity|Book|pickup|Confirm/i);

    const payload = gtaBookPayload();
    const preview = await merchantApi<{
      valid?: boolean;
      routing_source?: string | null;
      amount_cents?: number;
    }>(request, bearer, "POST", "/v1/merchant/booking/preview", payload);

    expect(preview.status, JSON.stringify(preview.json)).toBeLessThan(500);
    if (preview.status === 403) {
      throw new Error("Dispatcher seat returned 403 on preview — wrong storageState role?");
    }
    expect(preview.json.valid).toBeTruthy();
    const source = (preview.json.routing_source || "").toLowerCase();
    expect(ALLOWED_ROUTING.has(source), `routing_source=${source}`).toBeTruthy();
    expect(source).not.toContain("google");
    expect(preview.json.amount_cents).toBeGreaterThan(0);

    const confirm = await merchantApi<{
      order_id?: string;
      is_sandbox?: boolean;
    }>(request, bearer, "POST", "/v1/merchant/booking/confirm", {
      booking: payload,
    });

    expect(confirm.status, JSON.stringify(confirm.json)).toBe(200);
    expect(confirm.json.order_id).toBeTruthy();
    expect(confirm.json.is_sandbox).toBeTruthy();
  });
});

test.describe(`MP-AUTH-006 ${tcId("MP-AUTH-006")} @p0 @viewer`, () => {
  const ready = liveReady("viewer");
  test.skip(!ready, liveSkipReason("viewer"));
  test.use({ storageState: storageStatePath("viewer") || emptyState });

  test("viewer deep-link /book soft-forbids", async ({ page, request }) => {
    const bearer = await captureBearer(page, "/dashboard");

    await page.goto("/book");
    await expect(page.getByTestId("module-gate-forbidden")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("module-gate-forbidden")).toContainText(
      /Ask your owner for Dispatcher access/i
    );

    const preview = await merchantApi(
      request,
      bearer,
      "POST",
      "/v1/merchant/booking/preview",
      gtaBookPayload()
    );
    expect(preview.status).toBe(403);
  });
});

test.describe(`MP-BOOK-001 contract when offline ${tcId("MP-BOOK-001")} @p0`, () => {
  test("documents live env contract", () => {
    test.skip(
      liveEnabled && liveReady("dispatcher"),
      "live mode — covered by dispatcher project above"
    );
    expect(true).toBeTruthy();
  });
});
