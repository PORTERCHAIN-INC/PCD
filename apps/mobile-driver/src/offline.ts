import AsyncStorage from "@react-native-async-storage/async-storage";
import { fetchOfflineStatus, queueOffline, syncOffline } from "./api";
import type { OfflineSyncResult } from "./types";

const LOCAL_QUEUE_KEY = "porterchain_driver_offline_queue";
const GPS_BUFFER_KEY = "porterchain_driver_gps_buffer";

export type QueuedAction = {
  action_type: string;
  payload: Record<string, unknown>;
  client_id: string;
  created_at: string;
};

export type FlushResult = {
  queued: number;
  synced: boolean;
  gps_flushed: number;
  conflicts_resolved: number;
  failed: number;
  server_pending: number;
  server_failed: number;
};

function uuid(): string {
  return `m-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

async function readQueue(): Promise<QueuedAction[]> {
  try {
    const raw = await AsyncStorage.getItem(LOCAL_QUEUE_KEY);
    return raw ? (JSON.parse(raw) as QueuedAction[]) : [];
  } catch {
    return [];
  }
}

async function writeQueue(items: QueuedAction[]): Promise<void> {
  await AsyncStorage.setItem(LOCAL_QUEUE_KEY, JSON.stringify(items));
}

export async function enqueueOfflineAction(
  actionType: string,
  payload: Record<string, unknown>
): Promise<void> {
  const queue = await readQueue();
  queue.push({
    action_type: actionType,
    payload,
    client_id: uuid(),
    created_at: new Date().toISOString(),
  });
  await writeQueue(queue);
}

export async function enqueueGpsPing(ping: {
  lat: number;
  lng: number;
  accuracy_m?: number | null;
  heading?: number | null;
  speed_mps?: number | null;
  recorded_at?: string;
}): Promise<void> {
  const stamped = {
    ...ping,
    recorded_at: ping.recorded_at || new Date().toISOString(),
  };
  await AsyncStorage.setItem(GPS_BUFFER_KEY, JSON.stringify([stamped]));
}

export async function pendingOfflineCount(): Promise<number> {
  const local = (await readQueue()).length;
  try {
    const status = await fetchOfflineStatus();
    return local + (status.pending_count ?? 0);
  } catch {
    return local;
  }
}

export async function runOnlineOrQueue(
  actionType: string,
  payload: Record<string, unknown>,
  online: () => Promise<unknown>
): Promise<"online" | "queued"> {
  try {
    await online();
    return "online";
  } catch {
    await enqueueOfflineAction(actionType, payload);
    return "queued";
  }
}

export async function flushOfflineQueues(): Promise<FlushResult> {
  const queue = await readQueue();
  let queued = 0;
  for (const item of queue) {
    try {
      await queueOffline(item.action_type, item.payload, item.client_id);
      queued += 1;
    } catch {
      break;
    }
  }
  if (queued > 0) {
    await writeQueue(queue.slice(queued));
  }

  let gps_flushed = 0;
  try {
    const gpsRaw = await AsyncStorage.getItem(GPS_BUFFER_KEY);
    const gpsBuffer = gpsRaw ? (JSON.parse(gpsRaw) as Record<string, unknown>[]) : [];
    if (gpsBuffer.length) {
      const latest = gpsBuffer[gpsBuffer.length - 1];
      try {
        await queueOffline("location", latest);
        gps_flushed = 1;
        await AsyncStorage.removeItem(GPS_BUFFER_KEY);
      } catch {
        await AsyncStorage.setItem(GPS_BUFFER_KEY, JSON.stringify([latest]));
      }
    }
  } catch {
    /* keep buffer */
  }

  let synced = false;
  let conflicts_resolved = 0;
  let failed = 0;
  let syncResult: OfflineSyncResult | null = null;
  if (queued > 0 || gps_flushed > 0) {
    try {
      syncResult = await syncOffline();
      synced = true;
      conflicts_resolved = syncResult.conflicts_resolved ?? 0;
      failed = syncResult.failed ?? 0;
    } catch {
      synced = false;
    }
  }

  let server_pending = 0;
  let server_failed = 0;
  try {
    const status = await fetchOfflineStatus();
    server_pending = status.pending_count ?? 0;
    server_failed = status.failed_count ?? 0;
  } catch {
    /* local counts only */
  }

  return {
    queued,
    synced,
    gps_flushed,
    conflicts_resolved,
    failed: failed || server_failed,
    server_pending,
    server_failed,
  };
}
