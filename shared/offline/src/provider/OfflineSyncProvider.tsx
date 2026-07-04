import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useOnlineStatus, useAppState } from "@porterchain/mobile-hooks";
import { recordSyncLatency } from "@porterchain/mobile-performance";
import type {
  OfflineAction,
  OfflineStatus,
  OfflineSyncAdapter,
  OfflineSyncResult,
} from "@porterchain/mobile-api";
import {
  createEnterpriseOfflineQueue,
  createGpsBuffer,
  createUploadQueue,
  getLastSyncAt,
} from "@porterchain/mobile-storage";
import {
  registerBackgroundGpsTask,
  startBackgroundGps,
  stopBackgroundGps,
} from "../background-gps";
import { queueOfflineAction, runOfflineSync, summarizeLocalQueue } from "../sync-engine";

export type OfflineSyncProviderProps = {
  children: ReactNode;
  storeId: string;
  adapter: OfflineSyncAdapter;
  autoSyncIntervalMs?: number;
  enableBackgroundGps?: boolean;
  mode?: "driver" | "customer";
};

type OfflineSyncContextValue = {
  online: boolean;
  syncing: boolean;
  lastSyncAt: string | null;
  localPending: number;
  localFailed: number;
  uploadPending: number;
  gpsPending: number;
  serverStatus: OfflineStatus | null;
  queue: OfflineAction[];
  enqueue: (input: {
    actionType: string;
    payload: Record<string, unknown>;
    clientId?: string;
    localUri?: string;
  }) => OfflineAction | null;
  enqueueGps: (ping: {
    lat: number;
    lng: number;
    accuracy_m?: number;
    heading?: number;
    speed_mps?: number;
  }) => void;
  syncNow: () => Promise<OfflineSyncResult>;
  retryFailed: () => Promise<OfflineSyncResult>;
  runDirectOrQueue: (
    actionType: string,
    payload: Record<string, unknown>,
    onlineExecute?: () => Promise<unknown>,
    localUri?: string
  ) => Promise<{ mode: "online" | "queued" }>;
};

const OfflineSyncContext = createContext<OfflineSyncContextValue | null>(null);

export function OfflineSyncProvider({
  children,
  storeId,
  adapter,
  autoSyncIntervalMs = 30000,
  enableBackgroundGps = false,
}: OfflineSyncProviderProps) {
  const online = useOnlineStatus();
  const appState = useAppState();
  const foreground = appState === "active";
  const queryClient = useQueryClient();
  const [syncing, setSyncing] = useState(false);
  const [lastSyncAt, setLastSyncAt] = useState<string | null>(() => getLastSyncAt(storeId));
  const syncingRef = useRef(false);

  const queue = useMemo(() => createEnterpriseOfflineQueue(storeId), [storeId]);
  const gpsBuffer = useMemo(() => createGpsBuffer(storeId), [storeId]);
  const uploadQueue = useMemo(() => createUploadQueue(storeId), [storeId]);

  const engineDeps = useMemo(
    () => ({ storeId, queue, gpsBuffer, uploadQueue, adapter }),
    [adapter, gpsBuffer, queue, storeId, uploadQueue]
  );

  const statusQuery = useQuery({
    queryKey: ["offline", storeId, "server-status"],
    queryFn: () => adapter.getStatus?.() ?? Promise.resolve(null),
    enabled: online && foreground && Boolean(adapter.getStatus),
    refetchInterval: foreground ? autoSyncIntervalMs : false,
  });

  const localSummary = useMemo(
    () => summarizeLocalQueue(queue, gpsBuffer.count(), uploadQueue.pendingCount()),
    [gpsBuffer, queue, uploadQueue]
  );

  const syncNow = useCallback(async () => {
    if (syncingRef.current) {
      return {
        queued: 0,
        uploaded: 0,
        gps_flushed: 0,
        synced: 0,
        failed: 0,
        conflicts_resolved: 0,
        synced_at: getLastSyncAt(storeId) ?? new Date().toISOString(),
      };
    }
    syncingRef.current = true;
    setSyncing(true);
    const started = Date.now();
    try {
      const result = await runOfflineSync(engineDeps);
      recordSyncLatency(Date.now() - started);
      setLastSyncAt(result.synced_at);
      await queryClient.invalidateQueries({ queryKey: ["offline", storeId] });
      if (adapter.getStatus) await statusQuery.refetch();
      return result;
    } finally {
      syncingRef.current = false;
      setSyncing(false);
    }
  }, [adapter, engineDeps, queryClient, statusQuery, storeId]);

  const retryFailed = useCallback(async () => {
    if (adapter.retryFailed) await adapter.retryFailed();
    return syncNow();
  }, [adapter, syncNow]);

  useEffect(() => {
    if (!online || !foreground || syncingRef.current) return;
    void syncNow();
  }, [foreground, online, syncNow]);

  useEffect(() => {
    if (!online || !foreground) return;
    const timer = setInterval(() => {
      if (!syncingRef.current) void syncNow();
    }, autoSyncIntervalMs);
    return () => clearInterval(timer);
  }, [autoSyncIntervalMs, foreground, online, syncNow]);

  useEffect(() => {
    if (!enableBackgroundGps) return;
    registerBackgroundGpsTask(() => gpsBuffer);
    void startBackgroundGps();
    return () => {
      void stopBackgroundGps();
    };
  }, [enableBackgroundGps, gpsBuffer]);

  const enqueue = useCallback(
    (input: Parameters<OfflineSyncContextValue["enqueue"]>[0]) =>
      queueOfflineAction(engineDeps, input),
    [engineDeps]
  );

  const enqueueGps = useCallback(
    (ping: Parameters<OfflineSyncContextValue["enqueueGps"]>[0]) => {
      gpsBuffer.enqueue(ping);
    },
    [gpsBuffer]
  );

  const runDirectOrQueue = useCallback(
    async (
      actionType: string,
      payload: Record<string, unknown>,
      onlineExecute?: () => Promise<unknown>,
      localUri?: string
    ) => {
      if (online && onlineExecute) {
        await onlineExecute();
        return { mode: "online" as const };
      }
      if (online && adapter.executeDirect) {
        await adapter.executeDirect(actionType, payload);
        return { mode: "online" as const };
      }
      enqueue({ actionType, payload, localUri });
      return { mode: "queued" as const };
    },
    [adapter, enqueue, online]
  );

  const value = useMemo(
    () => ({
      online,
      syncing,
      lastSyncAt,
      localPending: localSummary.local_pending,
      localFailed: localSummary.local_failed,
      uploadPending: localSummary.upload_pending,
      gpsPending: localSummary.gps_pending,
      serverStatus: statusQuery.data ?? null,
      queue: localSummary.rows,
      enqueue,
      enqueueGps,
      syncNow,
      retryFailed,
      runDirectOrQueue,
    }),
    [
      enqueue,
      enqueueGps,
      lastSyncAt,
      localSummary,
      online,
      retryFailed,
      runDirectOrQueue,
      statusQuery.data,
      syncNow,
      syncing,
    ]
  );

  return <OfflineSyncContext.Provider value={value}>{children}</OfflineSyncContext.Provider>;
}

export function useOfflineSync() {
  const ctx = useContext(OfflineSyncContext);
  if (!ctx) throw new Error("useOfflineSync must be used within OfflineSyncProvider");
  return ctx;
}

export { createDriverOfflineSyncAdapter } from "../adapters/driver";
export { createCustomerOfflineSyncAdapter } from "../adapters/customer";
