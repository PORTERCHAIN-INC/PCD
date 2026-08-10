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

export type EntityAlertsPayload = {
  recipient_type: string;
  recipient_id: string;
  recent: NotificationRecord[];
  preferences: Array<{
    category: string;
    email_enabled: boolean;
    push_enabled: boolean;
    sms_enabled: boolean;
    in_app_enabled: boolean;
    persisted: boolean;
  }>;
  settings: {
    quiet_hours_enabled: boolean;
    quiet_start_hour: number;
    quiet_end_hour: number;
    timezone: string;
  };
  devices: Array<{
    id: string;
    platform: string;
    device_name: string | null;
    app_version: string | null;
    last_seen_at: string | null;
    notification_permission: string | null;
  }>;
  care: {
    open_exceptions: number;
    open_support_tickets: number;
    open_claims: number;
  };
  muted_categories: string[];
  links: {
    notifications_history: string;
    notifications_devices: string;
  };
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
  entityAlerts: (
    t: string,
    params: { recipient_type: string; recipient_id: string; limit?: number }
  ) => {
    const q = new URLSearchParams({
      recipient_type: params.recipient_type,
      recipient_id: params.recipient_id,
      limit: String(params.limit ?? 15),
    });
    return adminFetch<EntityAlertsPayload>(`${B}/entity-alerts?${q}`, t);
  },
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
  sendTest: (
    t: string,
    body: {
      template_key: string;
      channel?: string;
      recipient_address?: string;
    }
  ) =>
    adminFetch<{ ok: boolean; notification_id: string | null; status: string }>(
      `${B}/send-test`,
      t,
      { method: "POST", body: JSON.stringify(body) }
    ),
  deliveryLogs: (t: string, id: string) =>
    adminFetch<
      Array<{
        id: string;
        channel: string;
        status: string;
        error: string | null;
        recipient: string;
        created_at: string | null;
      }>
    >(`${B}/${id}/delivery-logs`, t),
};
