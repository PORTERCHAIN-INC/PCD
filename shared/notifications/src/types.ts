export type InboxFilter = "all" | "unread" | "read";

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

export type NotificationCenterAdapter = {
  fetchInbox: (filter?: InboxFilter) => Promise<NotificationInboxResponse>;
  fetchHistory: () => Promise<NotificationInboxResponse>;
  markRead: (id: string) => Promise<void>;
  markArchive: (id: string) => Promise<void>;
  markAllRead: () => Promise<void>;
  getPreferences?: () => Promise<NotificationPreference[]>;
  updatePreference?: (
    pref: Partial<NotificationPreference> & { category: string }
  ) => Promise<NotificationPreference>;
};

export type DeepLinkHandler = (deepLink: string, item?: NotificationInboxItem) => void;

export type NotificationRealtimeEvent =
  | { type: "notification"; payload: NotificationInboxItem }
  | { type: "unread_count"; count: number }
  | { type: "pong" };
