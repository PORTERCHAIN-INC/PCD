import { driverApi } from "@/lib/api";

declare global {
  interface Window {
    /** Playwright / local harness only — bypasses real FCM getToken. */
    __PC_TEST_FCM_TOKEN__?: string;
  }
}

const LOCAL_QUEUE_KEY = "porterchain_driver_offline_queue";
const GPS_BUFFER_KEY = "porterchain_driver_gps_buffer";

export interface QueuedAction {
  action_type: string;
  payload: Record<string, unknown>;
  client_id: string;
  created_at: string;
}

function readQueue(): QueuedAction[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(LOCAL_QUEUE_KEY);
    return raw ? (JSON.parse(raw) as QueuedAction[]) : [];
  } catch {
    return [];
  }
}

function writeQueue(items: QueuedAction[]) {
  if (typeof window === "undefined") return;
  localStorage.setItem(LOCAL_QUEUE_KEY, JSON.stringify(items));
}

export function enqueueOfflineAction(action_type: string, payload: Record<string, unknown>) {
  const queue = readQueue();
  queue.push({
    action_type,
    payload,
    client_id: crypto.randomUUID(),
    created_at: new Date().toISOString(),
  });
  writeQueue(queue);
}

export function enqueueGpsPing(ping: {
  lat: number;
  lng: number;
  accuracy_m?: number;
  heading?: number;
  speed_mps?: number;
  recorded_at?: string;
}) {
  if (typeof window === "undefined") return;
  const stamped = {
    ...ping,
    recorded_at: ping.recorded_at || new Date().toISOString(),
  };
  localStorage.setItem(GPS_BUFFER_KEY, JSON.stringify([stamped]));
}

export async function flushOfflineQueues(): Promise<{
  queued: number;
  synced: boolean;
  gps_flushed: number;
}> {
  if (typeof window === "undefined") return { queued: 0, synced: false, gps_flushed: 0 };

  const queue = readQueue();
  let queued = 0;
  for (const item of queue) {
    try {
      await driverApi.queueOffline(item.action_type, item.payload);
      queued += 1;
    } catch {
      break;
    }
  }
  if (queued > 0) {
    writeQueue(queue.slice(queued));
  }

  const gpsRaw = localStorage.getItem(GPS_BUFFER_KEY);
  const gpsBuffer = gpsRaw ? (JSON.parse(gpsRaw) as Record<string, unknown>[]) : [];
  let gps_flushed = 0;
  if (gpsBuffer.length) {
    const latest = gpsBuffer[gpsBuffer.length - 1];
    try {
      await driverApi.queueOffline("location", latest);
      gps_flushed = 1;
      localStorage.removeItem(GPS_BUFFER_KEY);
    } catch {
      localStorage.setItem(GPS_BUFFER_KEY, JSON.stringify([latest]));
    }
  }

  let synced = false;
  if (queued > 0 || gps_flushed > 0) {
    try {
      await driverApi.syncOffline();
      synced = true;
    } catch {
      synced = false;
    }
  }

  return { queued, synced, gps_flushed };
}

export async function registerWebPush(): Promise<boolean> {
  if (typeof window === "undefined" || !("Notification" in window)) return false;
  try {
    const permission = await Notification.requestPermission();
    if (permission !== "granted") return false;
    const { isFcmRegistrationToken } = await import("@/lib/firebase-public");
    const testToken =
      typeof window !== "undefined" && window.__PC_TEST_FCM_TOKEN__
        ? window.__PC_TEST_FCM_TOKEN__
        : null;
    let token = testToken;
    if (!token) {
      const { getWebFcmToken } = await import("@/lib/firebase-messaging");
      token = await getWebFcmToken();
    }
    if (!token || !isFcmRegistrationToken(token)) return false;
    await driverApi.registerPush(token, "web");
    return true;
  } catch {
    return false;
  }
}
