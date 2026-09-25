"use client";

import { useEffect, useRef } from "react";
import { publicEnv } from "@/lib/env";

function apiWsBase(): string {
  const base = publicEnv.porterchainApiUrl.replace(/\/$/, "");
  return base.replace(/^http/, "ws");
}

export function useMerchantRealtime(
  enabled: boolean,
  orgId: string | undefined,
  getToken: () => Promise<string>,
  onRefresh: () => void
) {
  const onRefreshRef = useRef(onRefresh);
  onRefreshRef.current = onRefresh;
  const getTokenRef = useRef(getToken);
  getTokenRef.current = getToken;

  useEffect(() => {
    if (!enabled) return;

    let ws: WebSocket | null = null;
    let pingTimer: ReturnType<typeof setInterval> | null = null;
    let pollTimer: ReturnType<typeof setInterval> | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;
    let wsOpen = false;

    function clearPing() {
      if (pingTimer) {
        clearInterval(pingTimer);
        pingTimer = null;
      }
    }

    function startPollFallback() {
      if (pollTimer || cancelled) return;
      pollTimer = setInterval(() => {
        if (document.visibilityState === "visible") onRefreshRef.current();
      }, 60_000);
    }

    function stopPollFallback() {
      if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
    }

    function teardownSocket() {
      clearPing();
      if (ws) {
        ws.onclose = null;
        ws.close();
        ws = null;
      }
      wsOpen = false;
    }

    async function connect() {
      if (cancelled || document.hidden) return;
      teardownSocket();
      try {
        const token = await getTokenRef.current();
        if (cancelled || document.hidden) return;
        const merchant = orgId ? `&merchant_id=${encodeURIComponent(orgId)}` : "";
        ws = new WebSocket(
          `${apiWsBase()}/v1/notifications/ws?token=${encodeURIComponent(token)}&portal=merchant${merchant}`
        );

        ws.onopen = () => {
          wsOpen = true;
          stopPollFallback();
        };

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data as string) as { type?: string };
            if (
              msg.type === "notification" ||
              msg.type === "order_update" ||
              msg.type === "dashboard_refresh"
            ) {
              onRefreshRef.current();
            }
          } catch {
            onRefreshRef.current();
          }
        };

        ws.onclose = () => {
          clearPing();
          ws = null;
          wsOpen = false;
          startPollFallback();
          if (!cancelled && !document.hidden) {
            reconnectTimer = setTimeout(() => void connect(), 5000);
          }
        };

        pingTimer = setInterval(() => {
          if (ws?.readyState === WebSocket.OPEN) ws.send("ping");
        }, 30000);
      } catch {
        startPollFallback();
      }
    }

    function onVisibility() {
      if (document.hidden) {
        if (reconnectTimer) {
          clearTimeout(reconnectTimer);
          reconnectTimer = null;
        }
        teardownSocket();
        stopPollFallback();
        return;
      }
      void connect();
    }

    if (!document.hidden) void connect();
    const openSoon = window.setTimeout(() => {
      if (!cancelled && !wsOpen && !document.hidden) startPollFallback();
    }, 3000);
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      cancelled = true;
      window.clearTimeout(openSoon);
      if (reconnectTimer) clearTimeout(reconnectTimer);
      document.removeEventListener("visibilitychange", onVisibility);
      stopPollFallback();
      teardownSocket();
    };
  }, [enabled, orgId]);
}
