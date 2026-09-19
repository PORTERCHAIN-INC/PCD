import { Platform } from "react-native";
import type { PushState } from "./types";
import { acceptOrder, registerPush, rejectOrder, unregisterPush } from "./api";
import { orderIdFromPushData } from "./linking";
import { clearRememberedPushToken, readRememberedPushToken, rememberPushToken } from "./pushToken";

/** Must match FCM `categoryId` / APNs `category` for job_assigned pushes. */
export const JOB_OFFER_CATEGORY = "job_offer";
export const JOB_OFFER_ACCEPT = "accept";
export const JOB_OFFER_DECLINE = "decline";

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

async function ensureJobOfferCategory(
  Notifications: typeof import("expo-notifications")
): Promise<void> {
  await Notifications.setNotificationCategoryAsync(JOB_OFFER_CATEGORY, [
    {
      identifier: JOB_OFFER_ACCEPT,
      buttonTitle: "Accept",
      options: { opensAppToForeground: false },
    },
    {
      identifier: JOB_OFFER_DECLINE,
      buttonTitle: "Decline",
      options: { opensAppToForeground: false, isDestructive: true },
    },
  ]);
}

const ACTIVE_JOB_NOTIF_ID = "porterchain-active-job";

export async function setActiveJobNotification(
  job: {
    orderId: string;
    orderNumber?: string | null;
  } | null
): Promise<void> {
  const Notifications = await loadNotifications();
  if (!Notifications) return;
  try {
    await Notifications.dismissNotificationAsync(ACTIVE_JOB_NOTIF_ID).catch(() => undefined);
  } catch {
    /* ignore */
  }
  if (!job) return;
  await ensureJobOfferCategory(Notifications);
  await Notifications.scheduleNotificationAsync({
    identifier: ACTIVE_JOB_NOTIF_ID,
    content: {
      title: "Job in progress",
      body: job.orderNumber
        ? `Working ${job.orderNumber} — tap for details`
        : "Active job — tap for details",
      data: { order_id: job.orderId, categoryId: JOB_OFFER_CATEGORY },
      sticky: true,
      sound: undefined,
    },
    trigger: null,
  });
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

  await ensureJobOfferCategory(Notifications);

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

export type PushOpenPayload = {
  orderId: string | null;
  /** Default notification tap opens the job. Accept/Decline only open on API failure. */
  action: "open" | "accept" | "decline";
  error?: string;
};

async function handleJobOfferResponse(
  response: {
    actionIdentifier: string;
    notification: { request: { content: { data?: Record<string, unknown> } } };
  },
  onOpen: (payload: PushOpenPayload) => void
): Promise<void> {
  const orderId = orderIdFromPushData(dataFromResponse(response));
  const actionId = response.actionIdentifier;

  if (actionId === JOB_OFFER_ACCEPT && orderId) {
    try {
      await acceptOrder(orderId);
      onOpen({ orderId, action: "accept" });
    } catch (err) {
      onOpen({
        orderId,
        action: "accept",
        error: err instanceof Error ? err.message : "accept_failed",
      });
    }
    return;
  }

  if (actionId === JOB_OFFER_DECLINE && orderId) {
    try {
      await rejectOrder(orderId, "unavailable");
      onOpen({ orderId, action: "decline" });
    } catch (err) {
      onOpen({
        orderId,
        action: "decline",
        error: err instanceof Error ? err.message : "reject_failed",
      });
    }
    return;
  }

  onOpen({ orderId, action: "open" });
}

export function attachPushListeners(onOpen: (payload: PushOpenPayload) => void): () => void {
  let remove: (() => void) | undefined;
  void loadNotifications().then(async (Notifications) => {
    if (!Notifications) return;
    await ensureJobOfferCategory(Notifications);

    const cold = await Notifications.getLastNotificationResponseAsync();
    if (cold) {
      await handleJobOfferResponse(cold, onOpen);
    }

    const sub = Notifications.addNotificationResponseReceivedListener((response) => {
      void handleJobOfferResponse(response, onOpen);
    });
    remove = () => sub.remove();
  });
  return () => remove?.();
}
