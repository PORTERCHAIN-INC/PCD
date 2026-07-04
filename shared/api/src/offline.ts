export const DRIVER_OFFLINE_ACTIONS = {
  LOCATION: "location",
  ARRIVE_STOP: "arrive_stop",
  DELIVER_STOP: "deliver_stop",
  ACCEPT_ORDER: "accept_order",
  REJECT_ORDER: "reject_order",
  POD_PHOTO: "pod_photo",
  CAMERA_UPLOAD: "camera_upload",
  POD_SIGNATURE: "pod_signature",
  POD_BARCODE: "pod_barcode",
  POD_COMPLETE: "pod_complete",
  GENERATE_OTP: "generate_otp",
  OTP_VERIFY: "otp_verify",
  DOCUMENT_UPLOAD: "document_upload",
  INCIDENT: "incident",
  SUPPORT_TICKET: "support_ticket",
  SHIFT_START: "shift_start",
  SHIFT_END: "shift_end",
  SHIFT_BREAK: "shift_break",
  SHIFT_RESUME: "shift_resume",
  AVAILABILITY: "availability",
} as const;

export const CUSTOMER_OFFLINE_ACTIONS = {
  SUPPORT_CREATE: "customer.support.create",
  CLAIM_CREATE: "customer.claim.create",
} as const;

export type OfflineActionStatus =
  "queued" | "uploading" | "syncing" | "synced" | "failed" | "conflict";

export type OfflineAction = {
  id: string;
  client_id?: string;
  action_type: string;
  payload: Record<string, unknown>;
  created_at: string;
  status: OfflineActionStatus;
  retry_count: number;
  last_error?: string | null;
  entity_key?: string | null;
};

export type OfflineUploadItem = {
  id: string;
  client_id: string;
  action_type: string;
  local_uri: string;
  remote_url?: string | null;
  payload: Record<string, unknown>;
  created_at: string;
  status: "pending" | "uploading" | "uploaded" | "failed";
  retry_count: number;
  last_error?: string | null;
};

export type GpsPing = {
  lat: number;
  lng: number;
  accuracy_m?: number;
  heading?: number;
  speed_mps?: number;
  recorded_at: string;
};

export type OfflineActionRow = {
  id: string;
  action_type: string;
  payload: Record<string, unknown>;
  status: string;
  error: string | null;
  created_at: string | null;
};

export type OfflineStatus = {
  pending_count: number;
  failed_count: number;
  synced_count: number;
  gps_pending: number;
  camera_upload_pending: number;
  failed_uploads: number;
  pending: OfflineActionRow[];
  failed: OfflineActionRow[];
  last_sync_at: string | null;
};

export type OfflineSyncResult = {
  queued: number;
  uploaded: number;
  gps_flushed: number;
  synced: number;
  failed: number;
  conflicts_resolved: number;
  synced_at: string;
};

export type OfflineQueueAdapter = {
  enqueue: (
    action: Omit<OfflineAction, "id" | "created_at" | "status" | "retry_count">
  ) => OfflineAction;
  list: () => OfflineAction[];
  update: (id: string, patch: Partial<OfflineAction>) => OfflineAction | null;
  remove: (id: string) => void;
  clear: () => void;
};

export type OfflineSyncAdapter = {
  queueAction: (
    actionType: string,
    payload: Record<string, unknown>,
    clientId?: string
  ) => Promise<unknown>;
  sync: () => Promise<{
    synced: number;
    failed: number;
    conflicts_resolved?: number;
    synced_at?: string;
  }>;
  retryFailed: () => Promise<{
    synced: number;
    failed: number;
    retried: number;
    conflicts_resolved?: number;
  }>;
  getStatus?: () => Promise<OfflineStatus>;
  uploadFile?: (localUri: string) => Promise<string>;
  executeDirect?: (actionType: string, payload: Record<string, unknown>) => Promise<unknown>;
};

export type ConflictResolution = "server_wins" | "client_retry" | "skip";

export function entityKeyForAction(
  actionType: string,
  payload: Record<string, unknown>
): string | null {
  const orderId = payload.order_id ?? payload.orderId;
  const stopId = payload.stop_id ?? payload.stopId;
  if (typeof orderId === "string") return `${actionType}:${orderId}`;
  if (typeof stopId === "string") return `${actionType}:${stopId}`;
  return null;
}
