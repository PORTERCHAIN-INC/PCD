"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { liveMapApi, type LiveMapFilters, type LiveMapSnapshot } from "@/lib/live-map";
import { wsLiveMapUrl } from "@/lib/maps";

const POLL_MS = 8000;

export function useLiveMapData(filters?: LiveMapFilters) {
  const { getApiToken, isLoaded, isSignedIn, authReady } = useAdminAuth();
  const [data, setData] = useState<LiveMapSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const filtersKey = JSON.stringify(filters ?? {});

  const fetchSnapshot = useCallback(async () => {
    const token = await getApiToken();
    return liveMapApi.snapshot(token, filters);
  }, [getApiToken, filtersKey]);

  useEffect(() => {
    if (!authReady || !isLoaded) return;
    if (!isSignedIn && process.env.NODE_ENV !== "development") return;

    let cancelled = false;
    let pollTimer: ReturnType<typeof setInterval> | null = null;

    async function connectWs() {
      try {
        const token = await getApiToken();
        const ws = new WebSocket(wsLiveMapUrl(token));
        wsRef.current = ws;

        ws.onopen = () => {
          if (!cancelled) setConnected(true);
        };
        ws.onmessage = (ev) => {
          try {
            const msg = JSON.parse(ev.data as string) as { type: string; data: LiveMapSnapshot };
            if (msg.type === "snapshot" && !cancelled) {
              setData(msg.data);
              setError(null);
            }
          } catch {
            /* ignore malformed frames */
          }
        };
        ws.onerror = () => {
          if (!cancelled) setConnected(false);
        };
        ws.onclose = () => {
          if (!cancelled) {
            setConnected(false);
            startPolling();
          }
        };
      } catch {
        startPolling();
      }
    }

    function startPolling() {
      if (pollTimer) return;
      void (async () => {
        try {
          const snap = await fetchSnapshot();
          if (!cancelled) {
            setData(snap);
            setError(null);
          }
        } catch (e) {
          if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load map data");
        }
      })();
      pollTimer = setInterval(() => {
        void fetchSnapshot()
          .then((snap) => {
            if (!cancelled) setData(snap);
          })
          .catch(() => undefined);
      }, POLL_MS);
    }

    void connectWs();

    return () => {
      cancelled = true;
      wsRef.current?.close();
      wsRef.current = null;
      if (pollTimer) clearInterval(pollTimer);
    };
  }, [authReady, isLoaded, isSignedIn, getApiToken, fetchSnapshot, filtersKey]);

  const refresh = useCallback(async () => {
    try {
      const snap = await fetchSnapshot();
      setData(snap);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Refresh failed");
    }
  }, [fetchSnapshot]);

  return { data, error, connected, refresh };
}
