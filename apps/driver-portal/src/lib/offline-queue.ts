/**
 * Offline-first driver actions. Check-ins and scans that fail for lack of signal are kept
 * in order on the device and replayed when the phone is back online. Every action carries
 * a client id, so the server ignores a replay it has already applied.
 */

export type QueuedAction = {
  id: string;
  kind: "checkin" | "scan";
  orderId?: string;
  body: Record<string, unknown>;
  at: number;
};

export type Rejected = { action: QueuedAction; reason: string };

export interface QueueStore {
  read(): { queue: QueuedAction[]; rejected: Rejected[] };
  write(state: { queue: QueuedAction[]; rejected: Rejected[] }): void;
}

const KEY = "pc-driver-offline-v1";

export function localQueueStore(
  storage: Storage | undefined = globalThis.localStorage
): QueueStore {
  return {
    read() {
      try {
        const raw = storage?.getItem(KEY);
        const v = raw ? JSON.parse(raw) : null;
        return {
          queue: Array.isArray(v?.queue) ? v.queue : [],
          rejected: Array.isArray(v?.rejected) ? v.rejected : [],
        };
      } catch {
        return { queue: [], rejected: [] };
      }
    },
    write(state) {
      storage?.setItem(KEY, JSON.stringify(state));
    },
  };
}

export function newClientId(): string {
  return (
    globalThis.crypto?.randomUUID?.() ?? `c-${Date.now()}-${Math.random().toString(36).slice(2)}`
  );
}

/** No signal (fetch never reached the server), as opposed to the server saying no. */
export function isOfflineError(
  err: unknown,
  online: boolean = globalThis.navigator?.onLine ?? true
): boolean {
  return !online || err instanceof TypeError;
}

export function enqueue(store: QueueStore, action: QueuedAction): number {
  const s = store.read();
  if (!s.queue.some((a) => a.id === action.id)) s.queue.push(action);
  store.write(s);
  return s.queue.length;
}

/**
 * Replay in order. Stops at the first offline failure (keeps the rest). A server rejection
 * (e.g. a box not scanned) is moved to ``rejected`` so the driver sees it; later actions continue.
 */
export async function flush(
  store: QueueStore,
  send: (a: QueuedAction) => Promise<unknown>
): Promise<{ sent: number; left: number; rejected: number }> {
  const s = store.read();
  let sent = 0;
  while (s.queue.length) {
    const a = s.queue[0];
    try {
      await send(a);
      sent += 1;
    } catch (e) {
      if (isOfflineError(e)) break;
      s.rejected.push({ action: a, reason: e instanceof Error ? e.message : "rejected" });
    }
    s.queue.shift();
    store.write(s);
  }
  return { sent, left: s.queue.length, rejected: s.rejected.length };
}

export function clearRejected(store: QueueStore): void {
  const s = store.read();
  store.write({ ...s, rejected: [] });
}
