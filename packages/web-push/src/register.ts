"use client";

import { firebaseWebConfig, isFcmRegistrationToken } from "./config";

declare global {
  interface Window {
    /** Playwright / local harness only — bypasses real FCM getToken. */
    __PC_TEST_FCM_TOKEN__?: string;
  }
}

/**
 * Ask for notification permission, get this browser's FCM token and hand it to
 * the portal's API (`registerDevice`). Returns false on any refusal or failure.
 */
export async function registerBrowserPush(
  registerDevice: (fcmToken: string, permission: NotificationPermission) => Promise<unknown>
): Promise<boolean> {
  if (typeof window === "undefined" || !("Notification" in window)) return false;
  try {
    const permission = await Notification.requestPermission();
    if (permission !== "granted") return false;
    let fcmToken = window.__PC_TEST_FCM_TOKEN__ || null;
    if (!fcmToken) {
      if (!firebaseWebConfig()) return false;
      const { getWebFcmToken } = await import("./messaging");
      fcmToken = await getWebFcmToken();
    }
    if (!fcmToken || !isFcmRegistrationToken(fcmToken)) return false;
    await registerDevice(fcmToken, permission);
    return true;
  } catch {
    return false;
  }
}

export function browserDeviceName(): string {
  return typeof navigator !== "undefined" ? navigator.userAgent.slice(0, 120) : "web";
}
