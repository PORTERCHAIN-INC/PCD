import * as Notifications from "expo-notifications";

export async function setBadgeCount(count: number): Promise<void> {
  try {
    await Notifications.setBadgeCountAsync(Math.max(0, count));
  } catch {
    // Badge unsupported on some platforms.
  }
}

export async function clearBadge(): Promise<void> {
  await setBadgeCount(0);
}
