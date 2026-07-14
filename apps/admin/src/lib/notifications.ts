import { adminFetch } from "@/lib/api";

export type NotificationDashboard = {
  total: number;
  queued: number;
  failed: number;
  active_devices: number;
  templates: number;
};

export type NotificationRecord = {
  id: string;
  event_type: string | null;
  template_key: string;
  category: string;
  channel: string;
  priority: string;
  recipient_type: string;
  recipient_id: string;
  recipient_address: string | null;
  title: string;
  body: string;
  status: string;
  retry_count: number;
  failure_reason: string | null;
  created_at: string;
  sent_at: string | null;
  delivered_at: string | null;
};

export type NotificationDevice = {
  id: string;
  user_role: string;
  user_id: string;
  platform: string;
  device_name: string | null;
  app_version: string | null;
  last_seen_at: string | null;
};

export type NotificationTemplate = {
  key: string;
  category: string;
  subject: string;
};

export type InboxNotification = {
  id: string;
  title: string;
  body: string;
  priority: string;
  category: string;
  deep_link?: string | null;
  is_read: boolean;
  created_at: string;
};

const B = "/v1/admin/notifications";

export const notificationsApi = {
  dashboard: (t: string) => adminFetch<NotificationDashboard>(`${B}/dashboard`, t),
  queue: (t: string, params: Record<string, string> = {}) => {
    const q = new URLSearchParams(params).toString();
    return adminFetch<NotificationRecord[]>(`${B}/queue${q ? `?${q}` : ""}`, t);
  },
  history: (t: string, params: Record<string, string> = {}) => {
    const q = new URLSearchParams(params).toString();
    return adminFetch<NotificationRecord[]>(`${B}/history${q ? `?${q}` : ""}`, t);
  },
  failed: (t: string) => adminFetch<NotificationRecord[]>(`${B}/failed`, t),
  templates: (t: string) => adminFetch<NotificationTemplate[]>(`${B}/templates`, t),
  devices: (t: string) => adminFetch<NotificationDevice[]>(`${B}/devices`, t),
  retry: (t: string, id: string) =>
    adminFetch<{ ok: boolean }>(`${B}/retry/${id}`, t, { method: "POST" }),
  inbox: (t: string, limit = 100) =>
    adminFetch<{ unread_count: number; items: InboxNotification[] }>(
      `/v1/notifications/inbox?limit=${limit}`,
      t
    ),
  markRead: (t: string, id: string) =>
    adminFetch<{ ok: boolean }>(`/v1/notifications/inbox/${id}/read`, t, { method: "POST" }),
  markAllRead: (t: string) =>
    adminFetch<{ ok: boolean; marked: number }>("/v1/notifications/inbox/mark-all-read", t, {
      method: "POST",
    }),
};
