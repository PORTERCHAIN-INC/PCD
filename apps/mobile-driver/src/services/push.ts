import { Platform } from "react-native";
import { getFcmToken } from "@porterchain/mobile-notifications";
import type { DriverApi } from "@porterchain/mobile-api";

export type PushRegisterResult =
  | { ok: true }
  | { ok: false; reason: "permission_denied" | "api_error" };

export async function registerDriverPush(api: DriverApi): Promise<PushRegisterResult> {
  const token = await getFcmToken();
  if (!token) {
    return { ok: false, reason: "permission_denied" };
  }
  try {
    await api.registerPush(token, Platform.OS === "ios" ? "ios" : "android");
    return { ok: true };
  } catch {
    return { ok: false, reason: "api_error" };
  }
}
