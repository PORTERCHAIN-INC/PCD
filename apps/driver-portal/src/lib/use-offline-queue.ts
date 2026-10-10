"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { driverApi } from "@/lib/api";
import {
  clearRejected,
  enqueue,
  flush,
  isOfflineError,
  localQueueStore,
  newClientId,
  type QueuedAction,
  type Rejected,
} from "@/lib/offline-queue";

const FLUSH_MS = 20_000;

function send(a: QueuedAction): Promise<unknown> {
  if (a.kind === "scan") {
    return driverApi.scanPackage(
      a.orderId!,
      a.body as { qr_payload: string; phase: "pickup" | "delivery" }
    );
  }
  return driverApi.dispatchCheckin(a.body as Parameters<typeof driverApi.dispatchCheckin>[0]);
}

/** Run driver actions online when possible, queue them when not, replay when signal returns. */
export function useOfflineQueue(onSynced: () => void) {
  const store = useMemo(() => localQueueStore(), []);
  const [pending, setPending] = useState(0);
  const [rejected, setRejected] = useState<Rejected[]>([]);
  const [online, setOnline] = useState(true);

  const refresh = useCallback(() => {
    const s = store.read();
    setPending(s.queue.length);
    setRejected(s.rejected);
  }, [store]);

  const sync = useCallback(async () => {
    if (!store.read().queue.length) return;
    const out = await flush(store, send);
    refresh();
    if (out.sent) onSynced();
  }, [store, refresh, onSynced]);

  useEffect(() => {
    refresh();
    setOnline(navigator.onLine);
    const up = () => {
      setOnline(true);
      void sync();
    };
    const down = () => setOnline(false);
    window.addEventListener("online", up);
    window.addEventListener("offline", down);
    const t = window.setInterval(() => void sync(), FLUSH_MS);
    void sync();
    return () => {
      window.removeEventListener("online", up);
      window.removeEventListener("offline", down);
      window.clearInterval(t);
    };
  }, [refresh, sync]);

  /** Try now; on no signal, queue it and return ``null`` (the caller updates the screen locally). */
  const run = useCallback(
    async <T>(
      kind: QueuedAction["kind"],
      body: Record<string, unknown>,
      orderId?: string
    ): Promise<T | null> => {
      const action: QueuedAction = {
        id: String(body.client_id ?? newClientId()),
        kind,
        orderId,
        body,
        at: Date.now(),
      };
      if (store.read().queue.length === 0) {
        try {
          return (await send(action)) as T;
        } catch (e) {
          if (!isOfflineError(e)) throw e;
          setOnline(false);
        }
      }
      // Behind queued actions (or no signal): keep order, replay later.
      setPending(enqueue(store, action));
      return null;
    },
    [store]
  );

  const dismiss = useCallback(() => {
    clearRejected(store);
    refresh();
  }, [store, refresh]);

  return { online, pending, rejected, run, dismiss };
}
