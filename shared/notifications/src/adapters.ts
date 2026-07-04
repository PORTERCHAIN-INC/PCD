import type {
  InboxFilter,
  NotificationCenterAdapter,
  NotificationInboxResponse,
  NotificationPreference,
} from "./types";

type DriverNotificationApi = {
  driverNotificationInbox: () => Promise<NotificationInboxResponse>;
  driverNotificationHistory: () => Promise<NotificationInboxResponse>;
  markNotificationRead: (id: string) => Promise<unknown>;
  markNotificationArchive: (id: string) => Promise<unknown>;
  markAllNotificationsRead: () => Promise<unknown>;
  notificationPreferences: () => Promise<NotificationPreference[]>;
  updateNotificationPreference: (
    body: Partial<NotificationPreference> & { category: string }
  ) => Promise<NotificationPreference>;
};

type CustomerNotificationApi = {
  notificationInbox: (params?: {
    unreadOnly?: boolean;
    archived?: boolean;
  }) => Promise<NotificationInboxResponse>;
  notificationHistory: () => Promise<NotificationInboxResponse>;
  markNotificationRead: (id: string) => Promise<unknown>;
  markNotificationArchive: (id: string) => Promise<unknown>;
  markAllNotificationsRead: () => Promise<unknown>;
  notificationPreferences: () => Promise<NotificationPreference[]>;
  updateNotificationPreference: (
    body: Partial<NotificationPreference> & { category: string }
  ) => Promise<NotificationPreference>;
};

function filterToParams(filter?: InboxFilter) {
  if (filter === "unread") return { unreadOnly: true };
  return {};
}

export function createDriverNotificationAdapter(
  api: DriverNotificationApi
): NotificationCenterAdapter {
  return {
    fetchInbox: async (filter) => {
      const data = await api.driverNotificationInbox();
      if (filter === "read") {
        return { ...data, items: data.items.filter((item) => item.is_read) };
      }
      if (filter === "unread") {
        return { ...data, items: data.items.filter((item) => !item.is_read) };
      }
      return data;
    },
    fetchHistory: () => api.driverNotificationHistory(),
    markRead: async (id) => {
      await api.markNotificationRead(id);
    },
    markArchive: async (id) => {
      await api.markNotificationArchive(id);
    },
    markAllRead: async () => {
      await api.markAllNotificationsRead();
    },
    getPreferences: () => api.notificationPreferences(),
    updatePreference: (pref) => api.updateNotificationPreference(pref),
  };
}

export function createCustomerNotificationAdapter(
  api: CustomerNotificationApi
): NotificationCenterAdapter {
  return {
    fetchInbox: async (filter) => {
      const data = await api.notificationInbox(filterToParams(filter));
      if (filter === "read") {
        return { ...data, items: data.items.filter((item) => item.is_read) };
      }
      return data;
    },
    fetchHistory: () => api.notificationHistory(),
    markRead: async (id) => {
      await api.markNotificationRead(id);
    },
    markArchive: async (id) => {
      await api.markNotificationArchive(id);
    },
    markAllRead: async () => {
      await api.markAllNotificationsRead();
    },
    getPreferences: () => api.notificationPreferences(),
    updatePreference: (pref) => api.updateNotificationPreference(pref),
  };
}
