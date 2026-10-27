"use client";

import { browserDeviceName, registerBrowserPush as register } from "@porterchain/web-push/register";
import { notificationsApi } from "@/lib/notifications";

/** Register this browser for FCM push via shared /v1/notifications/devices/register. */
export function registerBrowserPush(
  getToken: () => Promise<string>,
  orgId?: string
): Promise<boolean> {
  return register(async (fcmToken, permission) =>
    notificationsApi.registerDevice(
      await getToken(),
      {
        fcm_token: fcmToken,
        platform: "web",
        device_name: browserDeviceName(),
        notification_permission: permission,
      },
      orgId
    )
  );
}
