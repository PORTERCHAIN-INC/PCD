import { Platform } from "react-native";
import type { PushState } from "./types";
import { registerPush, unregisterPush } from "./api";
import { orderIdFromPushData } from "./linking";
import { clearRememberedPushToken, readRememberedPushToken, rememberPushToken } from "./pushToken";

function isFcmToken(token: string): boolean {
  return token.includes(":APA91");
}

function preview(token: string): string {
  return token.length > 28 ? `${token.slice(0, 16)}…` : token;
}

const UNSUPPORTED: PushState = {
  kind: "unavailable",
  permission: "unsupported",
  tokenPreview: null,
  registered: false,
  detail: "Push SDK not loaded",
};

async function loadNotifications(): Promise<typeof import("expo-notifications") | null> {
  try {
    return await import("expo-notifications");
  } catch {
    return null;
  }
}

function dataFromResponse(response: {
  notification: { request: { content: { data?: Record<string, unknown> } } };
}): Record<string, unknown> | null {
  const data = response.notification.request.content.data;
  return data && typeof data === "object" ? (data as Record<string, unknown>) : null;
}

/** Best-effort server revoke before local sign-out (still has bearer). */
export async function unregisterRememberedPush(): Promise<void> {
  try {
    const token = await readRememberedPushToken();
    await unregisterPush(token);
  } catch {
    /* offline / already signed out */
  } finally {
    await clearRememberedPushToken();
  }
}

export async function collectPush(): Promise<PushState> {
  const Notifications = await loadNotifications();
  if (!Notifications) {
    return { ...UNSUPPORTED, detail: "expo-notifications not installed" };
  }

  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowBanner: true,
      shouldShowList: true,
      shouldShowAlert: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
    }),
  });

  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("ops_critical", {
      name: "Ops critical",
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 120, 250],
      sound: "default",
    });
    await Notifications.setNotificationChannelAsync("assignments", {
      name: "Assignments",
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 400, 200, 400],
      sound: "default",
    });
    await Notifications.setNotificationChannelAsync("tracking", {
      name: "Tracking",
      importance: Notifications.AndroidImportance.DEFAULT,
    });
  }

  const existing = await Notifications.getPermissionsAsync();
  let status = existing.status;
  if (status !== "granted") {
    const asked = await Notifications.requestPermissionsAsync();
    status = asked.status;
  }
  if (status !== "granted") {
    return {
      kind: "denied",
      permission: status,
      tokenPreview: null,
      registered: false,
      detail: "Notifications off — assignment alerts will not arrive",
    };
  }

  try {
    const device = await Notifications.getDevicePushTokenAsync();
    const token = typeof device.data === "string" ? device.data : "";
    if (isFcmToken(token)) {
      const platform = Platform.OS === "ios" ? "ios" : "android";
      try {
        await registerPush(token, platform);
        await rememberPushToken(token);
        return {
          kind: "fcm",
          permission: status,
          tokenPreview: preview(token),
          registered: true,
          detail: "FCM registered with Notification Engine",
        };
      } catch (err) {
        return {
          kind: "fcm",
          permission: status,
          tokenPreview: preview(token),
          registered: false,
          detail: err instanceof Error ? err.message : "register_failed",
        };
      }
    }
    if (Platform.OS === "ios") {
      return {
        kind: "apns",
        permission: status,
        tokenPreview: token ? preview(token) : null,
        registered: false,
        detail: "iOS Expo Go yields APNs, not FCM — native EAS build required",
      };
    }
    return {
      kind: "unavailable",
      permission: status,
      tokenPreview: token ? preview(token) : null,
      registered: false,
      detail: "Device token is not an FCM registration token",
    };
  } catch (err) {
    return {
      kind: "unavailable",
      permission: status,
      tokenPreview: null,
      registered: false,
      detail: err instanceof Error ? err.message : "token_unavailable",
    };
  }
}

export type PushOpenPayload = { orderId: string | null };

export function attachPushListeners(onOpen: (payload: PushOpenPayload) => void): () => void {
  let remove: (() => void) | undefined;
  void loadNotifications().then(async (Notifications) => {
    if (!Notifications) return;

    const cold = await Notifications.getLastNotificationResponseAsync();
    if (cold) {
      onOpen({ orderId: orderIdFromPushData(dataFromResponse(cold)) });
    }

    const sub = Notifications.addNotificationResponseReceivedListener((response) => {
      onOpen({ orderId: orderIdFromPushData(dataFromResponse(response)) });
    });
    remove = () => sub.remove();
  });
  return () => remove?.();
}
