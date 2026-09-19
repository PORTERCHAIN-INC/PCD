/**
 * GAP-07 / PUSH-C02 / MP-NTF-002 — Merchant Playwright P0.
 *
 * Contract checks always run (no Chromium).
 * Live browser path: MERCHANT_E2E_LIVE=1 (+ storage state).
 * Uses window.__PC_TEST_FCM_TOKEN__ so real Firebase VAPID is not required.
 */
import fs from "fs";
import path from "path";
import { test, expect, tcId, liveEnabled, storageStatePath } from "./fixtures";

const VALID_TEST_FCM = `430248198034:APA91${"p".repeat(140)}`;

test.describe(`MP-NTF-002 ${tcId("MP-NTF-002")} @p0 @push`, () => {
  test("web-push + SW + NotificationCenter wiring present", () => {
    const root = path.join(process.cwd(), "src");
    const webPush = fs.readFileSync(path.join(root, "lib/web-push.ts"), "utf8");
    expect(webPush).toContain("registerBrowserPush");
    expect(webPush).toContain("__PC_TEST_FCM_TOKEN__");
    expect(webPush).toContain("registerDevice");
    expect(webPush).toContain("orgId");

    const sw = fs.readFileSync(path.join(process.cwd(), "public/firebase-messaging-sw.js"), "utf8");
    expect(sw).toContain("onBackgroundMessage");
    expect(sw).not.toMatch(/firebase-auth/);

    const center = fs.readFileSync(
      path.join(root, "components/dashboard/NotificationCenter.tsx"),
      "utf8"
    );
    expect(center).toContain("Enable browser push");
    expect(center).toContain("registerBrowserPush");
    expect(center).toContain("enablePush");
  });
});

test.describe(`GAP-07 ${tcId("GAP-07")} live-when-ready @push`, () => {
  test("enable browser push posts FCM token with org (mocked)", async ({ browser }) => {
    test.skip(!liveEnabled, "set MERCHANT_E2E_LIVE=1 (merchant on :3001)");
    const state = storageStatePath("dispatcher") || storageStatePath("owner");
    test.skip(!state, "set MERCHANT_STORAGE_STATE_DISPATCHER or OWNER");

    const context = await browser.newContext({ storageState: state });
    const page = await context.newPage();

    await page.addInitScript((token) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (window as any).__PC_TEST_FCM_TOKEN__ = token;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (window as any).Notification = {
        permission: "granted",
        requestPermission: async () => "granted",
      };
    }, VALID_TEST_FCM);

    const captured: { body: Record<string, unknown> | null } = { body: null };
    await page.route("**/v1/notifications/devices/register", async (route) => {
      try {
        captured.body = route.request().postDataJSON() as Record<string, unknown>;
      } catch {
        captured.body = null;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ device_id: "test-device", registered: true }),
      });
    });

    await page.goto("/dashboard");
    const enable = page.getByRole("button", { name: /Enable browser push/i });
    await expect(enable).toBeVisible({ timeout: 15000 });
    await enable.click();

    await expect.poll(() => captured.body !== null, { timeout: 10000 }).toBeTruthy();
    const registerBody = captured.body;
    expect(registerBody?.fcm_token).toBe(VALID_TEST_FCM);
    expect(registerBody?.platform).toBe("web");

    await context.close();
  });
});
