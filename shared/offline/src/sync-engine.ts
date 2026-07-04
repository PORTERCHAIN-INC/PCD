import type {
  OfflineAction,
  OfflineQueueAdapter,
  OfflineSyncAdapter,
  OfflineSyncResult,
} from "@porterchain/mobile-api";
import { DRIVER_OFFLINE_ACTIONS } from "@porterchain/mobile-api";
import type { createGpsBuffer } from "@porterchain/mobile-storage";
import type { createUploadQueue } from "@porterchain/mobile-storage";
import { getLastSyncAt, setLastSyncAt } from "@porterchain/mobile-storage";

const UPLOAD_ACTIONS = new Set<string>([
  DRIVER_OFFLINE_ACTIONS.POD_PHOTO,
  DRIVER_OFFLINE_ACTIONS.CAMERA_UPLOAD,
  DRIVER_OFFLINE_ACTIONS.POD_SIGNATURE,
  DRIVER_OFFLINE_ACTIONS.DOCUMENT_UPLOAD,
]);

const MAX_RETRIES = 5;

export type SyncEngineDeps = {
  storeId: string;
  queue: OfflineQueueAdapter;
  gpsBuffer: ReturnType<typeof createGpsBuffer>;
  uploadQueue: ReturnType<typeof createUploadQueue>;
  adapter: OfflineSyncAdapter;
};

export async function runOfflineSync(deps: SyncEngineDeps): Promise<OfflineSyncResult> {
  const now = new Date().toISOString();
  let queued = 0;
  let uploaded = 0;
  let gps_flushed = 0;

  const uploads = deps.uploadQueue
    .list()
    .filter((row) => row.status === "pending" || row.status === "failed");
  for (const item of uploads) {
    if (item.retry_count >= MAX_RETRIES) continue;
    deps.uploadQueue.update(item.id, { status: "uploading" });
    try {
      const remoteUrl = deps.adapter.uploadFile
        ? await deps.adapter.uploadFile(item.local_uri)
        : item.local_uri;
      deps.uploadQueue.update(item.id, { status: "uploaded", remote_url: remoteUrl });
      const payload = { ...item.payload, file_url: remoteUrl };
      deps.queue.enqueue({
        client_id: item.client_id,
        action_type: item.action_type,
        payload,
        entity_key: item.client_id,
      });
      deps.uploadQueue.remove(item.id);
      uploaded += 1;
    } catch (error) {
      deps.uploadQueue.update(item.id, {
        status: "failed",
        retry_count: item.retry_count + 1,
        last_error: error instanceof Error ? error.message : "upload_failed",
      });
    }
  }

  const localRows = deps.queue.list().filter((row) => row.status !== "synced");
  for (const row of localRows) {
    if (row.retry_count >= MAX_RETRIES) continue;
    deps.queue.update(row.id, { status: "syncing" });
    try {
      await deps.adapter.queueAction(row.action_type, row.payload, row.client_id);
      deps.queue.remove(row.id);
      queued += 1;
    } catch (error) {
      deps.queue.update(row.id, {
        status: "failed",
        retry_count: row.retry_count + 1,
        last_error: error instanceof Error ? error.message : "queue_failed",
      });
    }
  }

  const gpsRows = deps.gpsBuffer.list();
  for (const ping of gpsRows) {
    try {
      await deps.adapter.queueAction(
        DRIVER_OFFLINE_ACTIONS.LOCATION,
        {
          lat: ping.lat,
          lng: ping.lng,
          accuracy_m: ping.accuracy_m,
          heading: ping.heading,
          speed_mps: ping.speed_mps,
        },
        `gps-${ping.recorded_at}`
      );
      gps_flushed += 1;
    } catch {
      break;
    }
  }
  if (gps_flushed > 0) {
    deps.gpsBuffer.remove(gps_flushed);
  }

  let synced = 0;
  let failed = 0;
  let conflicts_resolved = 0;

  if (queued > 0 || gps_flushed > 0) {
    const result = await deps.adapter.sync();
    synced = result.synced;
    failed = result.failed;
    conflicts_resolved = result.conflicts_resolved ?? 0;
    setLastSyncAt(deps.storeId, result.synced_at ?? now);
  } else {
    const last = getLastSyncAt(deps.storeId);
    if (last) {
      synced = 0;
    }
  }

  return {
    queued,
    uploaded,
    gps_flushed,
    synced,
    failed,
    conflicts_resolved,
    synced_at: getLastSyncAt(deps.storeId) ?? now,
  };
}

export function summarizeLocalQueue(
  queue: OfflineQueueAdapter,
  gpsCount: number,
  uploadCount: number
) {
  const rows = queue.list();
  const pending = rows.filter((row) => row.status === "queued" || row.status === "syncing");
  const failed = rows.filter((row) => row.status === "failed");
  const uploads = rows.filter((row) => UPLOAD_ACTIONS.has(row.action_type));
  const gps =
    rows.filter((row) => row.action_type === DRIVER_OFFLINE_ACTIONS.LOCATION).length + gpsCount;

  return {
    local_pending: pending.length + uploadCount,
    local_failed: failed.length,
    upload_pending: uploads.length + uploadCount,
    gps_pending: gps,
    rows,
  };
}

export type QueuedOfflineInput = {
  actionType: string;
  payload: Record<string, unknown>;
  clientId?: string;
  localUri?: string;
};

export function queueOfflineAction(
  deps: Pick<SyncEngineDeps, "queue" | "uploadQueue">,
  input: QueuedOfflineInput
): OfflineAction | null {
  const clientId = input.clientId ?? `${input.actionType}-${Date.now()}`;

  if (input.localUri && UPLOAD_ACTIONS.has(input.actionType)) {
    deps.uploadQueue.enqueue({
      client_id: clientId,
      action_type: input.actionType,
      local_uri: input.localUri,
      payload: input.payload,
    });
    return null;
  }

  return deps.queue.enqueue({
    client_id: clientId,
    action_type: input.actionType,
    payload: input.payload,
  });
}
