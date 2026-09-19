export interface PushDeviceInfo {
  id: string;
  platform: string;
  device_name: string | null;
  last_seen_at: string | null;
}

export interface PushStatus {
  firebase_enabled: boolean;
  fcm_configured: boolean;
  registered_devices: number;
  devices: PushDeviceInfo[];
}

export interface NotificationItem {
  id: string;
  title: string;
  body: string;
  priority: string;
  category: string;
  template_key: string;
  deep_link: string | null;
  is_read: boolean;
  created_at: string | null;
  group: string;
  order_id?: string;
  ticket_id?: string;
  claim_id?: string;
}

export interface OfflineActionRow {
  id: string;
  action_type: string;
  payload: Record<string, unknown>;
  status: string;
  error: string | null;
  created_at: string | null;
}

export interface OfflineStatus {
  pending_count: number;
  failed_count: number;
  synced_count: number;
  gps_pending: number;
  camera_upload_pending: number;
  failed_uploads: number;
  pending: OfflineActionRow[];
  failed: OfflineActionRow[];
  last_sync_at: string | null;
}

export interface DriverCommunicationsSnapshot {
  push: PushStatus;
  notifications: {
    unread_count: number;
    items: NotificationItem[];
    by_group: Record<string, NotificationItem[]>;
  };
  offline: OfflineStatus;
  realtime: { enabled: boolean; websocket_path: string };
  auto_sync: { enabled: boolean; interval_seconds: number };
  last_updated: string;
}

export const NOTIFICATION_GROUP_LABELS: Record<string, string> = {
  assignment: "Assignments",
  route_changes: "Route Changes",
  emergency: "Emergency Alerts",
  support: "Support Messages",
  claims: "Claims Updates",
};

export function groupLabel(group: string): string {
  return NOTIFICATION_GROUP_LABELS[group] ?? group;
}

export function formatCommTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
