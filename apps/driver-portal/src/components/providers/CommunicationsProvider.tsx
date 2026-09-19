"use client";

import { useEffect } from "react";
import { flushOfflineQueues, registerWebPush } from "@/lib/offline-client";

const AUTO_SYNC_MS = 30_000;

export function CommunicationsProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    registerWebPush().catch(() => undefined);

    const sync = () => {
      if (document.visibilityState !== "visible") return;
      void flushOfflineQueues();
    };

    sync();
    const interval = window.setInterval(sync, AUTO_SYNC_MS);
    const onOnline = () => void flushOfflineQueues();
    window.addEventListener("online", onOnline);

    return () => {
      window.clearInterval(interval);
      window.removeEventListener("online", onOnline);
    };
  }, []);

  return <>{children}</>;
}
