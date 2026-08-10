"use client";

import { useEffect, useRef, useState } from "react";
import { AlertTriangle, Timer, X } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import type { OpsStats } from "@/lib/operations";

type Toast = {
  id: number;
  kind: "exception" | "sla";
  message: string;
};

function beep() {
  try {
    const ctx = new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = 880;
    gain.gain.value = 0.04;
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.12);
    void ctx.close();
  } catch {
    // Autoplay / AudioContext may be blocked — silent fail.
  }
}

/** Watch KPI deltas and surface a toast (+ optional beep) when risk rises. */
export function OpsAlertToast({
  stats,
  soundEnabled,
}: {
  stats: OpsStats | null;
  soundEnabled: boolean;
}) {
  const prev = useRef<{ exceptions: number; sla: number } | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const seq = useRef(0);

  useEffect(() => {
    if (!stats) return;
    const exceptions = stats.open_exceptions;
    const sla = (stats.sla_at_risk ?? 0) + (stats.sla_breached ?? 0);
    const last = prev.current;
    prev.current = { exceptions, sla };
    if (!last) return;

    const next: Toast[] = [];
    if (exceptions > last.exceptions) {
      next.push({
        id: ++seq.current,
        kind: "exception",
        message: `${exceptions - last.exceptions} new exception${exceptions - last.exceptions === 1 ? "" : "s"} — ${exceptions} open`,
      });
    }
    if (sla > last.sla) {
      next.push({
        id: ++seq.current,
        kind: "sla",
        message: `SLA pressure rising — ${sla} at risk / breached`,
      });
    }
    if (next.length === 0) return;
    if (soundEnabled) beep();
    setToasts((t) => [...t, ...next].slice(-4));
    // When the tab is idle, also fire a browser notification (permission-gated).
    if (typeof document !== "undefined" && document.hidden && "Notification" in window) {
      const notify = () => {
        for (const t of next) {
          try {
            new Notification("PorterChain Ops", { body: t.message, tag: `ops-${t.kind}` });
          } catch {
            /* ignored */
          }
        }
      };
      if (Notification.permission === "granted") notify();
      else if (Notification.permission === "default") {
        void Notification.requestPermission().then((p) => {
          if (p === "granted") notify();
        });
      }
    }
  }, [stats, soundEnabled]);

  useEffect(() => {
    if (toasts.length === 0) return;
    const timer = setTimeout(() => setToasts((t) => t.slice(1)), 6000);
    return () => clearTimeout(timer);
  }, [toasts]);

  if (toasts.length === 0) return null;

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-80 flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={cn(
            "pointer-events-auto flex items-start gap-2 rounded-xl border bg-white p-3 shadow-lg",
            t.kind === "exception" ? "border-amber-200" : "border-red-200"
          )}
        >
          {t.kind === "exception" ? (
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
          ) : (
            <Timer className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />
          )}
          <p className="flex-1 text-sm text-primary">{t.message}</p>
          <button
            onClick={() => setToasts((all) => all.filter((x) => x.id !== t.id))}
            className="rounded p-0.5 text-muted hover:bg-gray-bg"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}

/** Adaptive poll interval (ms) — faster when the tower is under pressure. */
export function adaptivePollMs(stats: OpsStats | null): number {
  if (!stats) return 15_000;
  const pressure =
    stats.open_exceptions +
    stats.delayed_orders +
    (stats.sla_at_risk ?? 0) +
    (stats.sla_breached ?? 0) * 2;
  if (pressure >= 10) return 5_000;
  if (pressure >= 3) return 10_000;
  return 20_000;
}
