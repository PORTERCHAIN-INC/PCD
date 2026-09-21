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

  useEffect(() => {
    if (!enabled) return;

    let ws: WebSocket | null = null;
    let pingTimer: ReturnType<typeof setInterval> | null = null;
    let pollTimer: ReturnType<typeof setInterval> | null = null;
    let cancelled = false;

    async function connect() {
      try {
        const token = await getToken();
        if (cancelled) return;
        const merchant = orgId ? `&merchant_id=${encodeURIComponent(orgId)}` : "";
        ws = new WebSocket(
          `${apiWsBase()}/v1/notifications/ws?token=${encodeURIComponent(token)}&portal=merchant${merchant}`
        );

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
          if (!cancelled) {
            window.setTimeout(() => void connect(), 5000);
          }
        };

        pingTimer = setInterval(() => {
          if (ws?.readyState === WebSocket.OPEN) ws.send("ping");
        }, 30000);
      } catch {
        /* fall back to polling */
      }
    }

    void connect();
    pollTimer = setInterval(() => onRefreshRef.current(), 60000);

    return () => {
      cancelled = true;
      if (pingTimer) clearInterval(pingTimer);
      if (pollTimer) clearInterval(pollTimer);
      ws?.close();
    };
  }, [enabled, orgId, getToken]);
}
