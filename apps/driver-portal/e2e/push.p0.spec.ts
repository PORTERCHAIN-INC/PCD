/**
 * Driver web push contract — registerWebPush + FCM SW (no Firebase Auth).
 *
 * Contract checks always run (no Chromium).
 * Live path: DRIVER_E2E_LIVE=1 when storage/fixture exists.
 */
import fs from "fs";
import path from "path";
import { test, expect, tcId } from "./fixtures";

test.describe(`UI-D-PUSH ${tcId("UI-D-PUSH")} @p0 @push`, () => {
  test("registerWebPush + SW wiring present (FCM-only)", () => {
    const root = path.join(process.cwd(), "src");
    const offline = fs.readFileSync(path.join(root, "lib/offline-client.ts"), "utf8");
    expect(offline).toContain("registerWebPush");
    expect(offline).toContain("__PC_TEST_FCM_TOKEN__");
    expect(offline).toContain("registerPush");
    expect(offline).toContain("isFcmRegistrationToken");

    const sw = fs.readFileSync(path.join(process.cwd(), "public/firebase-messaging-sw.js"), "utf8");
    expect(sw).toContain("onBackgroundMessage");
    expect(sw).not.toMatch(/firebase-auth/);

    const messaging = fs.readFileSync(path.join(root, "lib/firebase-messaging.ts"), "utf8");
    expect(messaging).toContain("getWebFcmToken");
    expect(messaging).toContain("firebase-messaging-sw.js");
  });
});
