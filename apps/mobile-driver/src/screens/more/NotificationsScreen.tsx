import { NotificationCenter, NotificationSettingsScreen } from "@porterchain/mobile-notifications";

export function NotificationsScreen() {
  return (
    <NotificationCenter
      title="Notifications"
      subtitle="Assignments, routes, and alerts"
      settingsSlot={<NotificationSettingsScreen />}
    />
  );
}
