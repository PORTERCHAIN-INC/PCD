import { Platform } from "react-native";
import { getFcmToken } from "@porterchain/mobile-notifications";
import type { DriverApi } from "@porterchain/mobile-api";

export async function registerDriverPush(api: DriverApi) {
  const token = await getFcmToken();
  if (!token) return false;
  try {
    await api.registerPush(token, Platform.OS === "ios" ? "ios" : "android");
    return true;
  } catch {
    return false;
  }
}
