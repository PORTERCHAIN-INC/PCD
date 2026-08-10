"use client";

import { useEffect, useRef } from "react";
import {
  INACTIVITY_ACTIVITY_THROTTLE_MS,
  INACTIVITY_CHECK_MS,
  INACTIVITY_STORAGE_KEY,
  INACTIVITY_TIMEOUT_MS,
  clearActivityMarker,
  isInactive,
  markActivity,
} from "./inactivity";

export type UseInactivityTimeoutOptions = {
  /** When false, listeners are not attached. */
  enabled?: boolean;
  timeoutMs?: number;
  onTimeout: () => void | Promise<void>;
};

/**
 * Signs the user out after `timeoutMs` without pointer/keyboard/touch/scroll activity.
 * Syncs last-activity across same-origin tabs via localStorage.
 */
export function useInactivityTimeout({
  enabled = true,
  timeoutMs = INACTIVITY_TIMEOUT_MS,
  onTimeout,
}: UseInactivityTimeoutOptions): void {
  const onTimeoutRef = useRef(onTimeout);
  onTimeoutRef.current = onTimeout;
  const firedRef = useRef(false);

  useEffect(() => {
    if (!enabled || typeof window === "undefined") return;

    firedRef.current = false;
    markActivity();

    const bump = () => {
      if (firedRef.current) return;
      markActivity();
    };

    let lastMove = 0;
    const onMove = () => {
      const now = Date.now();
      if (now - lastMove < INACTIVITY_ACTIVITY_THROTTLE_MS) return;
      lastMove = now;
      bump();
    };

    const fire = () => {
      if (firedRef.current) return;
      if (!isInactive(timeoutMs)) return;
      firedRef.current = true;
      clearActivityMarker();
      void onTimeoutRef.current();
    };

    const onVisibility = () => {
      if (document.visibilityState === "visible") fire();
    };

    const onStorage = (event: StorageEvent) => {
      if (event.key === INACTIVITY_STORAGE_KEY && event.newValue) {
        /* another tab marked activity — reset local fire latch */
        firedRef.current = false;
      }
    };

    const opts: AddEventListenerOptions = { passive: true };
    window.addEventListener("pointerdown", bump, opts);
    window.addEventListener("keydown", bump, opts);
    window.addEventListener("touchstart", bump, opts);
    window.addEventListener("scroll", bump, opts);
    window.addEventListener("mousemove", onMove, opts);
    window.addEventListener("focus", fire);
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("storage", onStorage);

    const interval = window.setInterval(fire, INACTIVITY_CHECK_MS);
    fire();

    return () => {
      window.removeEventListener("pointerdown", bump);
      window.removeEventListener("keydown", bump);
      window.removeEventListener("touchstart", bump);
      window.removeEventListener("scroll", bump);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("focus", fire);
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("storage", onStorage);
      window.clearInterval(interval);
    };
  }, [enabled, timeoutMs]);
}
