"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { driverApi } from "@/lib/api";
import { flushOfflineQueues, registerWebPush } from "@/lib/offline-client";
import { publicEnv } from "@/lib/env";

export function useDriverCommunications() {
  const qc = useQueryClient();
  const [syncing, setSyncing] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const mounted = useRef(true);
  const wsRef = useRef<WebSocket | null>(null);

  const query = useQuery({
    queryKey: ["driver-communications"],
    queryFn: () => driverApi.communicationsHub(),
  });

  const refresh = useCallback(async () => {
    await qc.invalidateQueries({ queryKey: ["driver-communications"] });
  }, [qc]);

  const syncOffline = useCallback(async () => {
    setSyncing(true);
    try {
      await flushOfflineQueues();
      await driverApi.syncOffline().catch(() => undefined);
      await driverApi.retryOffline().catch(() => undefined);
      await refresh();
    } finally {
      if (mounted.current) setSyncing(false);
    }
  }, [refresh]);

  useEffect(() => {
    mounted.current = true;
    const onOnline = () => {
      void syncOffline();
      void refresh();
    };
    window.addEventListener("online", onOnline);
    return () => {
      mounted.current = false;
      window.removeEventListener("online", onOnline);
    };
  }, [refresh, syncOffline]);

  useEffect(() => {
    let cancelled = false;

    async function connectWs() {
      const sessionRes = await fetch("/api/auth/ws-token", { credentials: "include" });
      if (!sessionRes.ok) return;
      const session = (await sessionRes.json()) as { token?: string };
      const token = session.token;
      if (!token || cancelled) return;

      const base = publicEnv.porterchainApiUrl.replace(/^http/, "ws");
      const url = `${base}/v1/notifications/ws?token=${encodeURIComponent(token)}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!cancelled) setWsConnected(true);
      };
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data as string) as { type?: string };
          if (msg.type !== "pong") void refresh();
        } catch {
          void refresh();
        }
      };
      ws.onclose = () => {
        if (!cancelled) setWsConnected(false);
      };
    }

    void connectWs().catch(() => undefined);

    const ping = window.setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send("ping");
      }
    }, 25_000);

    return () => {
      cancelled = true;
      window.clearInterval(ping);
      wsRef.current?.close();
    };
  }, [refresh]);

  const markRead = useCallback(
    async (notificationId: string) => {
      await driverApi.markNotificationRead(notificationId);
      await refresh();
    },
    [refresh]
  );

  return {
    data: query.data ?? null,
    error: query.error instanceof Error ? query.error.message : "",
    loading: query.isLoading && !query.data,
    refreshing: query.isFetching && Boolean(query.data),
    syncing,
    wsConnected,
    refresh,
    syncOffline,
    markRead,
    registerPush: registerWebPush,
  };
}
