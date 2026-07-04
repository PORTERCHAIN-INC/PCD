import { driverApi } from "@/lib/api";

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
}) {
  if (typeof window === "undefined") return;
  const raw = localStorage.getItem(GPS_BUFFER_KEY);
  const buffer = raw ? (JSON.parse(raw) as typeof ping[]) : [];
  buffer.push(ping);
  if (buffer.length > 500) buffer.splice(0, buffer.length - 500);
  localStorage.setItem(GPS_BUFFER_KEY, JSON.stringify(buffer));
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
  for (const ping of gpsBuffer) {
    try {
      await driverApi.queueOffline("location", ping);
      gps_flushed += 1;
    } catch {
      break;
    }
  }
  if (gps_flushed > 0) {
    localStorage.setItem(GPS_BUFFER_KEY, JSON.stringify(gpsBuffer.slice(gps_flushed)));
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
  const permission = await Notification.requestPermission();
  if (permission !== "granted") return false;
  const token = `web-${crypto.randomUUID()}`;
  await driverApi.registerPush(token, "web");
  return true;
}
