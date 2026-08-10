"use client";

import { useEffect, useRef } from "react";
import { publicEnv } from "@/lib/env";

function apiWsBase(): string {
  const base = publicEnv.porterchainApiUrl.replace(/\/$/, "");
  return base.replace(/^http/, "ws");
}

/** Live notification WS for admin bell — falls back to polling when disconnected. */
export function useAdminNotificationRealtime(
  enabled: boolean,
  getToken: () => Promise<string>,
  onEvent: () => void
) {
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!enabled) return;

    let ws: WebSocket | null = null;
    let pingTimer: ReturnType<typeof setInterval> | null = null;
    let cancelled = false;

    async function connect() {
      try {
        const token = await getToken();
        if (cancelled) return;
        ws = new WebSocket(`${apiWsBase()}/v1/notifications/ws?token=${encodeURIComponent(token)}`);

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data as string) as { type?: string };
            if (msg.type === "notification" || msg.type === "dashboard_refresh") {
              onEventRef.current();
            }
          } catch {
            onEventRef.current();
          }
        };

        ws.onclose = () => {
          if (!cancelled) {
            window.setTimeout(() => void connect(), 5000);
          }
        };

        pingTimer = setInterval(() => {
          if (ws?.readyState === WebSocket.OPEN) ws.send("ping");
        }, 30000);
      } catch {
        /* rely on React Query poll fallback */
      }
    }

    void connect();

    return () => {
      cancelled = true;
      if (pingTimer) clearInterval(pingTimer);
      ws?.close();
    };
  }, [enabled, getToken]);
}
