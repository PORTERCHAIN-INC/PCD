"use client";

import { useEffect, useState } from "react";

const INTERACTION_EVENTS = ["pointerdown", "keydown", "scroll", "touchstart"] as const;

/** Defer heavy third-party scripts until the user engages or a timeout elapses. */
export function useDeferUntilInteraction(timeoutMs = 12_000): boolean {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (ready) return;

    let done = false;
    const activate = () => {
      if (done) return;
      done = true;
      setReady(true);
    };

    for (const event of INTERACTION_EVENTS) {
      window.addEventListener(event, activate, { once: true, passive: true });
    }

    const timer = window.setTimeout(activate, timeoutMs);

    return () => {
      window.clearTimeout(timer);
      for (const event of INTERACTION_EVENTS) {
        window.removeEventListener(event, activate);
      }
    };
  }, [ready, timeoutMs]);

  return ready;
}
