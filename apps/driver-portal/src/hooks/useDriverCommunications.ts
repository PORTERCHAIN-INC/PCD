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
    let attempt = 0;
    let retryTimer: number | undefined;

    // Reconnect with backoff after any close (deploy, Wi-Fi blip, sleep). Each attempt fetches a
    // fresh ws token: Clerk session tokens expire in ~60 s, so reusing one would fail.
    const scheduleReconnect = () => {
      if (cancelled) return;
      const delay = Math.min(30_000, 1_000 * 2 ** attempt) + Math.floor(Math.random() * 500);
      attempt += 1;
      retryTimer = window.setTimeout(() => void connectWs().catch(scheduleReconnect), delay);
    };

    async function connectWs() {
      const sessionRes = await fetch("/api/auth/ws-token", { credentials: "include" });
      if (sessionRes.status === 401) return; // signed out: the page handles it
      if (!sessionRes.ok) throw new Error("ws_token_unavailable");
      const session = (await sessionRes.json()) as { token?: string };
      const token = session.token;
      if (cancelled) return;
      if (!token) throw new Error("ws_token_missing");

      const base = publicEnv.porterchainApiUrl.replace(/^http/, "ws");
      const url = `${base}/v1/notifications/ws?token=${encodeURIComponent(token)}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        attempt = 0;
        if (!cancelled) setWsConnected(true);
        void refresh(); // catch up on anything missed while disconnected
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
        if (wsRef.current === ws) wsRef.current = null;
        if (!cancelled) {
          setWsConnected(false);
          scheduleReconnect();
        }
      };
    }

    void connectWs().catch(scheduleReconnect);

    const ping = window.setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send("ping");
      }
    }, 25_000);

    return () => {
      cancelled = true;
      window.clearInterval(ping);
      if (retryTimer) window.clearTimeout(retryTimer);
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
