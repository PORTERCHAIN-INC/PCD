"use client";

import { notificationsApi } from "@/lib/notifications";

declare global {
  interface Window {
    /** Playwright / local harness only — bypasses real FCM getToken. */
    __PC_TEST_FCM_TOKEN__?: string;
  }
}

/** Register this browser for FCM push via shared /v1/notifications/devices/register. */
export async function registerBrowserPush(
  getToken: () => Promise<string>,
  orgId?: string
): Promise<boolean> {
  if (typeof window === "undefined" || !("Notification" in window)) return false;
  try {
    const permission = await Notification.requestPermission();
    if (permission !== "granted") return false;

    const { isFcmRegistrationToken, firebaseWebConfig } = await import("@/lib/firebase-public");
    const testToken =
      typeof window !== "undefined" && window.__PC_TEST_FCM_TOKEN__
        ? window.__PC_TEST_FCM_TOKEN__
        : null;
    let fcmToken = testToken;
    if (!fcmToken) {
      if (!firebaseWebConfig()) return false;
      const { getWebFcmToken } = await import("@/lib/firebase-messaging");
      fcmToken = await getWebFcmToken();
    }
    if (!fcmToken || !isFcmRegistrationToken(fcmToken)) return false;
    const authToken = await getToken();
    await notificationsApi.registerDevice(
      authToken,
      {
        fcm_token: fcmToken,
        platform: "web",
        device_name: typeof navigator !== "undefined" ? navigator.userAgent.slice(0, 120) : "web",
        notification_permission: permission,
      },
      orgId
    );
    return true;
  } catch {
    return false;
  }
}
