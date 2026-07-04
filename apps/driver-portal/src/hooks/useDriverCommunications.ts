"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { driverApi } from "@/lib/api";
import type { DriverCommunicationsSnapshot } from "@/lib/communications";
import { flushOfflineQueues, registerWebPush } from "@/lib/offline-client";
import { publicEnv } from "@/lib/env";

const POLL_MS = 15_000;

export function useDriverCommunications() {
  const [data, setData] = useState<DriverCommunicationsSnapshot | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const mounted = useRef(true);
  const wsRef = useRef<WebSocket | null>(null);

  const refresh = useCallback(async (silent = false) => {
    if (!silent) setRefreshing(true);
    try {
      const snap = await driverApi.communicationsHub();
      if (mounted.current) {
        setData(snap);
        setError("");
      }
    } catch (e) {
      if (mounted.current) setError(e instanceof Error ? e.message : "communications_refresh_failed");
    } finally {
      if (mounted.current) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, []);

  const syncOffline = useCallback(async () => {
    setSyncing(true);
    try {
      await flushOfflineQueues();
      await driverApi.syncOffline().catch(() => undefined);
      await driverApi.retryOffline().catch(() => undefined);
      await refresh(true);
    } finally {
      if (mounted.current) setSyncing(false);
    }
  }, [refresh]);

  useEffect(() => {
    mounted.current = true;
    refresh();
    registerWebPush().catch(() => undefined);

    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") refresh(true);
    }, POLL_MS);

    const onOnline = () => {
      void syncOffline();
      void refresh(true);
    };
    window.addEventListener("online", onOnline);

    return () => {
      mounted.current = false;
      window.clearInterval(interval);
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
          if (msg.type !== "pong") void refresh(true);
        } catch {
          void refresh(true);
        }
      };
      ws.onclose = () => {
        if (!cancelled) setWsConnected(false);
      };
    }

    connectWs().catch(() => undefined);

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
      await refresh(true);
    },
    [refresh]
  );

  return {
    data,
    error,
    loading,
    refreshing,
    syncing,
    wsConnected,
    refresh: () => refresh(true),
    syncOffline,
    markRead,
    registerPush: registerWebPush,
  };
}
