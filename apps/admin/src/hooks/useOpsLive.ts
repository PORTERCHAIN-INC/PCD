"use client";

import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { apiWsBase, resolveWsToken } from "@/hooks/useAdminNotificationRealtime";
import { applyDriverFix, staleKeysFor, type LiveMsg } from "@/lib/today";
import type { LiveMapSnapshot } from "@/lib/operations";

export type LiveStatus = "connecting" | "live" | "polling";

const BACKOFF_MS = [1000, 2000, 5000, 10000, 30000];

/**
 * Ops Today real-time: one WebSocket to the API (Redis pub/sub fan-out).
 * GPS fixes patch the cached map in place; order/exception events mark queries stale
 * (debounced). While disconnected the page keeps its 15 s poll — status tells it which.
 */
export function useOpsLive(enabled = true): LiveStatus {
  const qc = useQueryClient();
  const { getApiToken } = useAdminAuth();
  const tokenRef = useRef(getApiToken);
  tokenRef.current = getApiToken;
  const [status, setStatus] = useState<LiveStatus>("connecting");

  useEffect(() => {
    if (!enabled) return;
    let ws: WebSocket | null = null;
    let cancelled = false;
    let attempt = 0;
    let retry: ReturnType<typeof setTimeout> | null = null;
    let ping: ReturnType<typeof setInterval> | null = null;
    let flush: ReturnType<typeof setTimeout> | null = null;
    const stale = new Set<string>();

    const invalidateSoon = (keys: string[]) => {
      keys.forEach((k) => stale.add(k));
      if (flush) return;
      flush = setTimeout(() => {
        flush = null;
        const keys = [...stale];
        stale.clear();
        for (const k of keys) void qc.invalidateQueries({ queryKey: ["admin", k] });
      }, 400);
    };

    const onMessage = (raw: string) => {
      let msg: LiveMsg;
      try {
        msg = JSON.parse(raw) as LiveMsg;
      } catch {
        return;
      }
      if (msg.type === "hello") {
        attempt = 0;
        setStatus("live");
        // Catch up on anything missed while disconnected.
        invalidateSoon([
          "today-stats",
          "today-exceptions",
          "today-queue",
          "today-eta",
          "today-map",
        ]);
        return;
      }
      if (msg.type === "driver") {
        qc.setQueryData<LiveMapSnapshot>(
          ["admin", "today-map"],
          (s) => applyDriverFix(s, msg) ?? s
        );
        return;
      }
      invalidateSoon(staleKeysFor(msg));
    };

    const scheduleReconnect = () => {
      if (cancelled) return;
      setStatus("polling");
      const wait = BACKOFF_MS[Math.min(attempt, BACKOFF_MS.length - 1)];
      attempt += 1;
      retry = setTimeout(() => void connect(), wait);
    };

    async function connect() {
      if (cancelled) return;
      if (document.hidden) {
        retry = setTimeout(() => void connect(), 5000);
        return;
      }
      setStatus((s) => (s === "live" ? s : "connecting"));
      try {
        const token = await resolveWsToken(() => tokenRef.current());
        if (cancelled) return;
        if (!token) return scheduleReconnect();
        ws = new WebSocket(
          `${apiWsBase()}/v1/admin/operations/live/ws?token=${encodeURIComponent(token)}`
        );
        ws.onmessage = (e) => onMessage(String(e.data));
        ws.onclose = () => {
          if (ping) clearInterval(ping);
          ping = null;
          ws = null;
          scheduleReconnect();
        };
        ping = setInterval(() => ws?.readyState === WebSocket.OPEN && ws.send("ping"), 25_000);
      } catch {
        scheduleReconnect();
      }
    }

    void connect();
    return () => {
      cancelled = true;
      if (retry) clearTimeout(retry);
      if (ping) clearInterval(ping);
      if (flush) clearTimeout(flush);
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    };
  }, [enabled, qc]);

  return status;
}
