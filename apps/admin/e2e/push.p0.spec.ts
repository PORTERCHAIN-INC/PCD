/**
 * GAP-01 / UI-NTF-003 / PushHealthStrip — Playwright P0.
 *
 * Contract checks always run (no Chromium).
 * Live browser path: ADMIN_RUN_LIVE=1 (+ optional ADMIN_STORAGE_STATE).
 * Uses window.__PC_TEST_FCM_TOKEN__ so real Firebase VAPID is not required.
 */
import fs from "fs";
import path from "path";
import { test, expect, tcId } from "./fixtures";

const VALID_TEST_FCM = `430248198034:APA91${"p".repeat(140)}`;

test.describe(`UI-NTF-003 ${tcId("UI-NTF-003")} @p0 @push`, () => {
  test("web-push + SW + PushHealthStrip wiring present", () => {
    const root = path.join(process.cwd(), "src");
    const webPush = fs.readFileSync(path.join(root, "lib/web-push.ts"), "utf8");
    expect(webPush).toContain("registerBrowserPush");
    expect(webPush).toContain("__PC_TEST_FCM_TOKEN__");
    expect(webPush).toContain("registerDevice");

    const sw = fs.readFileSync(path.join(process.cwd(), "public/firebase-messaging-sw.js"), "utf8");
    expect(sw).toContain("onBackgroundMessage");
    expect(sw).not.toMatch(/firebase-auth/);

    const strip = fs.readFileSync(
      path.join(root, "components/operations/PushHealthStrip.tsx"),
      "utf8"
    );
    expect(strip).toContain('data-testid="ops-push-health"');
    expect(strip).toContain("notificationsApi.pushHealth");

    const notifPage = fs.readFileSync(path.join(root, "app/(ops)/notifications/page.tsx"), "utf8");
    expect(notifPage).toContain("Enable browser push");
    expect(notifPage).toContain("registerBrowserPush");
  });
});

test.describe(`GAP-01 ${tcId("GAP-01")} live-when-ready @push`, () => {
  test("enable browser push posts FCM token (mocked)", async ({ page }) => {
    test.skip(
      !process.env.ADMIN_RUN_LIVE,
      "set ADMIN_RUN_LIVE=1 (admin on :3002, storage state if needed)"
    );

    await page.addInitScript((token) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (window as any).__PC_TEST_FCM_TOKEN__ = token;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (window as any).Notification = {
        permission: "granted",
        requestPermission: async () => "granted",
      };
    }, VALID_TEST_FCM);

    let registerBody: Record<string, unknown> | null = null;
    await page.route("**/v1/notifications/devices/register", async (route) => {
      try {
        registerBody = route.request().postDataJSON() as Record<string, unknown>;
      } catch {
        registerBody = null;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ device_id: "test-device", registered: true }),
      });
    });

    await page.route("**/v1/admin/notifications/push-health", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          tone: "ok",
          issues: [],
          fcm: {
            sdk_available: true,
            credentials_configured: true,
            production_ready: true,
            production_ready_reason: null,
            project_id: "porterchain-test",
            push_enabled: true,
            push_send: true,
            app_env: "local",
          },
          devices: { admin_active: 1, admin_users: 1, driver_active: 0 },
          critical_24h: { total: 0, delivered: 0, failed: 0 },
          last_urgent_push: null,
        }),
      });
    });

    await page.goto("/operations");
    await expect(page.getByTestId("ops-push-health")).toBeVisible({ timeout: 15000 });

    await page.goto("/notifications?tab=devices");
    const enable = page.getByRole("button", { name: /Enable browser push/i });
    await expect(enable).toBeVisible({ timeout: 15000 });
    await enable.click();

    await expect.poll(() => registerBody !== null, { timeout: 10000 }).toBeTruthy();
    expect(registerBody?.fcm_token).toBe(VALID_TEST_FCM);
    expect(registerBody?.platform).toBe("web");
  });
});

test.describe(`UI-OPS PushHealthStrip ${tcId("UI-OPS-001")} live-when-ready @push`, () => {
  test("operations shows push health strip", async ({ page }) => {
    test.skip(!process.env.ADMIN_RUN_LIVE, "set ADMIN_RUN_LIVE=1");

    await page.route("**/v1/admin/notifications/push-health", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          tone: "warn",
          issues: ["No admin browsers registered — staff risk alerts email-only"],
          fcm: {
            sdk_available: true,
            credentials_configured: false,
            production_ready: false,
            production_ready_reason: "missing",
            project_id: null,
            push_enabled: true,
            push_send: true,
            app_env: "local",
          },
          devices: { admin_active: 0, admin_users: 0, driver_active: 0 },
          critical_24h: { total: 0, delivered: 0, failed: 0 },
          last_urgent_push: null,
        }),
      });
    });

    await page.goto("/operations");
    await expect(page.getByTestId("ops-push-health")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("ops-push-health")).toContainText(/Push/i);
  });
});
