import { Platform } from "react-native";
import * as Notifications from "expo-notifications";

const CHANNELS = [
  { id: "default", name: "General", importance: Notifications.AndroidImportance.DEFAULT },
  { id: "high", name: "Important", importance: Notifications.AndroidImportance.HIGH },
  {
    id: "critical",
    name: "Critical alerts",
    importance: Notifications.AndroidImportance.MAX,
    bypassDnd: true,
    vibrationPattern: [0, 250, 250, 250],
  },
] as const;

export async function setupNotificationChannels(): Promise<void> {
  if (Platform.OS !== "android") return;

  for (const channel of CHANNELS) {
    await Notifications.setNotificationChannelAsync(channel.id, {
      name: channel.name,
      importance: channel.importance,
      bypassDnd: channel.id === "critical",
      vibrationPattern: "vibrationPattern" in channel ? [...channel.vibrationPattern] : undefined,
      sound: "default",
      enableVibrate: true,
      showBadge: true,
    });
  }
}

export function channelForPriority(priority?: string): string {
  if (priority === "critical") return "critical";
  if (priority === "high") return "high";
  return "default";
}
