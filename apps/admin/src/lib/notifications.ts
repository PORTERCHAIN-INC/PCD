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
  inbox: (t: string) => adminFetch<{ unread_count: number; items: Array<Record<string, unknown>> }>("/v1/notifications/inbox", t),
};
