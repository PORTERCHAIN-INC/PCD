"use client";

import { useEffect, useRef } from "react";
import { publicEnv } from "@/lib/env";
import { STAFF_COOKIE_TOKEN } from "@/lib/staff-session";

function apiWsBase(): string {
  const base = publicEnv.porterchainApiUrl.replace(/\/$/, "");
  return base.replace(/^http/, "ws");
}

async function resolveWsToken(getToken: () => Promise<string>): Promise<string | null> {
  const token = await getToken();
  if (!token) return null;
  if (token === "dev" || token.startsWith("staff_sess_")) return token;
  if (token === STAFF_COOKIE_TOKEN) {
    const res = await fetch("/api/auth/ws-token", { cache: "no-store" });
    if (!res.ok) return null;
    const body = (await res.json()) as { token?: string };
    return typeof body.token === "string" ? body.token : null;
  }
  return token;
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
        const token = await resolveWsToken(getToken);
        if (cancelled || !token) return;
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
