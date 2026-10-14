import AsyncStorage from "@react-native-async-storage/async-storage";
import { randomUUID } from "expo-crypto";
import { fetchOfflineStatus, queueOffline, syncOffline } from "./api";
import { ApiError, isApiError, isNetworkError } from "./netErrors";
import { isTransientRejection, shouldPark } from "./replayPolicy";
import { deleteSecureBlob, readSecureBlob, wipeSecureBlobs, writeSecureBlob } from "./secureBlob";
import type { OfflineSyncResult } from "./types";

const LOCAL_QUEUE_KEY = "porterchain_driver_offline_queue";
const REJECTED_KEY = "porterchain_driver_offline_rejected";
const GPS_BUFFER_KEY = "porterchain_driver_gps_buffer";

/** Payload fields that are personal data. They are encrypted to disk, never kept in AsyncStorage. */
const SENSITIVE_KEYS = ["file_url", "photo_url", "signature_data", "otp"] as const;

export type QueuedAction = {
  action_type: string;
  /** Non-sensitive fields only (ids, flags). */
  payload: Record<string, unknown>;
  /** Encrypted file holding the sensitive fields, if any. */
  blob_id?: string | null;
  client_id: string;
  created_at: string;
  /** Set when the server rejected the action during a sync. */
  rejected_reason?: string;
  /** Auth/permission (401/403) replays so far; capped so a real 403 cannot block forever. */
  auth_attempts?: number;
};

export type FlushResult = {
  queued: number;
  synced: boolean;
  gps_flushed: number;
  conflicts_resolved: number;
  failed: number;
  /** Actions the server refused on replay; kept locally and shown to the driver, never dropped. */
  rejected: number;
  server_pending: number;
  server_failed: number;
};

/** Collision-proof idempotency key (RFC 4122 v4 from the platform CSPRNG). Server dedupes on it. */
export function newClientId(): string {
  return randomUUID();
}

// One writer at a time: every read-modify-write of the queue goes through this chain.
let lock: Promise<unknown> = Promise.resolve();
function withLock<T>(work: () => Promise<T>): Promise<T> {
  const run = lock.then(work, work);
  lock = run.catch(() => undefined);
  return run;
}

async function readList(key: string): Promise<QueuedAction[]> {
  const raw = await AsyncStorage.getItem(key);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as QueuedAction[];
  } catch {
    return [];
  }
}

/** Throws if storage is full or broken, so the caller can tell the driver instead of losing work. */
async function writeList(key: string, items: QueuedAction[]): Promise<void> {
  await AsyncStorage.setItem(key, JSON.stringify(items));
}

export function readQueue(): Promise<QueuedAction[]> {
  return readList(LOCAL_QUEUE_KEY);
}

export function readRejected(): Promise<QueuedAction[]> {
  return readList(REJECTED_KEY);
}

function splitPayload(payload: Record<string, unknown>) {
  const plain: Record<string, unknown> = {};
  const secret: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(payload)) {
    if ((SENSITIVE_KEYS as readonly string[]).includes(k) && v != null && v !== "") secret[k] = v;
    else plain[k] = v;
  }
  return { plain, secret };
}

export async function enqueueOfflineAction(
  actionType: string,
  payload: Record<string, unknown>
): Promise<QueuedAction> {
  const { plain, secret } = splitPayload(payload);
  const blob_id = Object.keys(secret).length ? await writeSecureBlob(secret) : null;
  const item: QueuedAction = {
    action_type: actionType,
    payload: plain,
    blob_id,
    client_id: newClientId(),
    created_at: new Date().toISOString(),
  };
  try {
    await withLock(async () => {
      const queue = await readQueue();
      queue.push(item);
      await writeList(LOCAL_QUEUE_KEY, queue);
    });
  } catch (err) {
    if (blob_id) deleteSecureBlob(blob_id);
    throw new Error("offline_queue_full", { cause: err });
  }
  return item;
}

export async function enqueueGpsPing(ping: {
  lat: number;
  lng: number;
  accuracy_m?: number | null;
  heading?: number | null;
  speed_mps?: number | null;
  recorded_at?: string;
}): Promise<void> {
  // Live position only: the latest point replaces the previous one (no trail is kept on device).
  const stamped = { ...ping, recorded_at: ping.recorded_at || new Date().toISOString() };
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

/** Stops whose completion is saved on the phone but not yet on the server ("Delivered, syncing"). */
export async function queuedStopIds(): Promise<string[]> {
  const queue = await readQueue();
  return queue
    .filter((q) => q.action_type === "deliver_stop" && typeof q.payload.stop_id === "string")
    .map((q) => q.payload.stop_id as string);
}

/**
 * Run the action online. Queue it ONLY when there was no HTTP response (offline / timeout).
 * A server rejection (4xx/5xx) is rethrown so the driver sees it — it is never shown as done.
 * If older actions are still queued, new ones queue behind them to keep server-side order.
 */
export async function runOnlineOrQueue(
  actionType: string,
  payload: Record<string, unknown>,
  online: () => Promise<unknown>
): Promise<"online" | "queued"> {
  if ((await readQueue()).length > 0) {
    await enqueueOfflineAction(actionType, payload);
    return "queued";
  }
  try {
    await online();
    return "online";
  } catch (err) {
    if (!isNetworkError(err)) throw err;
    await enqueueOfflineAction(actionType, payload);
    return "queued";
  }
}

async function pushQueue(): Promise<{ queued: number; rejected: number }> {
  return withLock(async () => {
    // Older builds parked actions on auth/permission blips; put those back in line.
    const parkedNow = await readRejected();
    const revive = parkedNow.filter((a) => isTransientRejection(a.rejected_reason));
    if (revive.length) {
      await writeList(
        REJECTED_KEY,
        parkedNow.filter((a) => !revive.includes(a))
      );
      await writeList(LOCAL_QUEUE_KEY, [
        ...revive.map(({ rejected_reason: _r, ...a }) => ({ ...a, auth_attempts: 0 })),
        ...(await readQueue()),
      ]);
    }
    let queue = await readQueue();
    let queued = 0;
    let rejected = 0;
    while (queue.length) {
      const item = queue[0];
      let full = item.payload;
      let unreadable = false;
      if (item.blob_id) {
        try {
          full = {
            ...item.payload,
            ...(await readSecureBlob<Record<string, unknown>>(item.blob_id)),
          };
        } catch {
          unreadable = true; // key or file gone (e.g. device restore): never send half a proof
        }
      }
      try {
        if (unreadable) throw new ApiError("pod_blob_unreadable", 422);
        await queueOffline(item.action_type, full, item.client_id);
        if (item.blob_id) deleteSecureBlob(item.blob_id);
        queued += 1;
      } catch (err) {
        const attempts = (item.auth_attempts ?? 0) + 1;
        if (isApiError(err) && shouldPark(err.status, attempts - 1)) {
          const parked = await readRejected();
          parked.push({ ...item, rejected_reason: err.message });
          await writeList(REJECTED_KEY, parked);
          rejected += 1;
        } else {
          if (isApiError(err) && (err.status === 401 || err.status === 403)) {
            await writeList(LOCAL_QUEUE_KEY, [
              { ...item, auth_attempts: attempts },
              ...queue.slice(1),
            ]);
          }
          break; // offline, auth blip or server error: keep it and everything after it, retry later
        }
      }
      queue = queue.slice(1);
      await writeList(LOCAL_QUEUE_KEY, queue);
    }
    return { queued, rejected };
  });
}

export async function flushOfflineQueues(): Promise<FlushResult> {
  const { queued, rejected } = await pushQueue();

  let gps_flushed = 0;
  try {
    const gpsRaw = await AsyncStorage.getItem(GPS_BUFFER_KEY);
    const gpsBuffer = gpsRaw ? (JSON.parse(gpsRaw) as Record<string, unknown>[]) : [];
    const latest = gpsBuffer[gpsBuffer.length - 1];
    if (latest) {
      await queueOffline("location", latest);
      gps_flushed = 1;
      await AsyncStorage.removeItem(GPS_BUFFER_KEY);
    }
  } catch {
    /* keep buffer for next flush */
  }

  let synced = false;
  let conflicts_resolved = 0;
  let failed = 0;
  if (queued > 0 || gps_flushed > 0) {
    try {
      const syncResult: OfflineSyncResult = await syncOffline();
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
    rejected: Math.max(rejected, (await readRejected()).length),
    server_pending,
    server_failed,
  };
}

/** Sign-out: remove every queued action, rejected action, GPS point, encrypted file and the key. */
export async function wipeOfflineData(): Promise<void> {
  await withLock(async () => {
    await AsyncStorage.multiRemove([LOCAL_QUEUE_KEY, REJECTED_KEY, GPS_BUFFER_KEY]);
  });
  await wipeSecureBlobs();
}
