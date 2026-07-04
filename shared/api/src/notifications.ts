import type { ApiClient } from "./client";

export type NotificationInboxItem = {
  id: string;
  title: string;
  body: string;
  priority?: string;
  category?: string;
  deep_link?: string | null;
  is_read: boolean;
  is_archived?: boolean;
  created_at: string | null;
  group?: string;
  order_id?: string;
  ticket_id?: string;
  claim_id?: string;
};

export type NotificationInboxResponse = {
  unread_count: number;
  items: NotificationInboxItem[];
  by_group?: Record<string, NotificationInboxItem[]>;
};

export type NotificationPreference = {
  category: string;
  email_enabled: boolean;
  push_enabled: boolean;
  sms_enabled: boolean;
  in_app_enabled: boolean;
};

export function createNotificationApi(client: ApiClient, v1 = "/v1") {
  const base = `${v1}/notifications`;

  return {
    registerDevice: (body: {
      fcm_token: string;
      platform: "ios" | "android" | "expo";
      device_name?: string;
      app_version?: string;
      os_version?: string;
      language?: string;
      timezone?: string;
      notification_permission?: string;
    }) => client.post<{ device_id: string; registered: boolean }>(`${base}/devices/register`, body),

    revokeDevice: (deviceId: string) =>
      client.delete(`${base}/devices/${encodeURIComponent(deviceId)}`),

    inbox: (params?: { unreadOnly?: boolean; archived?: boolean; limit?: number }) => {
      const qs = new URLSearchParams();
      if (params?.unreadOnly) qs.set("unread_only", "true");
      if (params?.archived) qs.set("archived", "true");
      if (params?.limit) qs.set("limit", String(params.limit));
      const query = qs.toString();
      return client.get<NotificationInboxResponse>(`${base}/inbox${query ? `?${query}` : ""}`);
    },

    history: (limit = 100) =>
      client.get<NotificationInboxResponse>(`${base}/inbox/history?limit=${limit}`),

    markRead: (id: string) => client.post(`${base}/inbox/${encodeURIComponent(id)}/read`),

    markArchive: (id: string) => client.post(`${base}/inbox/${encodeURIComponent(id)}/archive`),

    markAllRead: () => client.post<{ ok: boolean; marked: number }>(`${base}/inbox/mark-all-read`),

    getPreferences: () => client.get<NotificationPreference[]>(`${base}/preferences`),

    updatePreference: (body: Partial<NotificationPreference> & { category: string }) =>
      client.patch<NotificationPreference>(`${base}/preferences`, body),
  };
}

export type NotificationApi = ReturnType<typeof createNotificationApi>;
