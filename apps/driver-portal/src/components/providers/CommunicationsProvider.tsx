"use client";

import { useEffect } from "react";
import { flushOfflineQueues, registerWebPush } from "@/lib/offline-client";

const AUTO_SYNC_MS = 30_000;

export function CommunicationsProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    let cancelled = false;

    const runPush = () => {
      if (cancelled) return;
      void registerWebPush().catch(() => undefined);
    };

    // Defer past first paint so jobs/dashboard win the main-thread + network race.
    // Matches admin AdminAuthProvider FCM idle deferral.
    const idle =
      typeof window.requestIdleCallback === "function"
        ? window.requestIdleCallback(runPush, { timeout: 4000 })
        : window.setTimeout(runPush, 2500);

    const sync = () => {
      if (document.visibilityState !== "visible") return;
      void flushOfflineQueues();
    };

    // Also defer first offline flush slightly so it does not contend with page queries.
    const flushTimer = window.setTimeout(sync, 1500);
    const interval = window.setInterval(sync, AUTO_SYNC_MS);
    const onOnline = () => void flushOfflineQueues();
    window.addEventListener("online", onOnline);

    return () => {
      cancelled = true;
      if (typeof window.cancelIdleCallback === "function" && typeof idle === "number") {
        window.cancelIdleCallback(idle);
      } else {
        window.clearTimeout(idle as number);
      }
      window.clearTimeout(flushTimer);
      window.clearInterval(interval);
      window.removeEventListener("online", onOnline);
    };
  }, []);

  return <>{children}</>;
}
