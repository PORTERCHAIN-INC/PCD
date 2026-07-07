import { NotificationCenter, NotificationSettingsScreen } from "@porterchain/mobile-notifications";

export function NotificationsScreen() {
  return (
    <NotificationCenter
      title="Notifications"
      subtitle="Shipment updates and receipts"
      settingsSlot={<NotificationSettingsScreen />}
    />
  );
}
