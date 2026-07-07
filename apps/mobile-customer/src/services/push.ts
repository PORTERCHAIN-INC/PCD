import { Platform } from "react-native";
import { getFcmToken } from "@porterchain/mobile-notifications";
import type { CustomerApi } from "@porterchain/mobile-api";
import { useSettingsStore } from "../store/settings-store";

export async function registerCustomerPush(api: CustomerApi) {
  const token = await getFcmToken();
  if (!token) return false;

  try {
    await api.registerPushDevice({
      fcm_token: token,
      platform: Platform.OS === "ios" ? "ios" : "android",
      device_name: Platform.OS,
      notification_permission: true,
    });
    return true;
  } catch {
    return false;
  }
}

export function recordForegroundNotification(title: string, body: string) {
  useSettingsStore.getState().pushLocalNotification(title, body);
}
