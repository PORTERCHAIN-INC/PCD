"use client";

import { useSyncExternalStore } from "react";

const noopSubscribe = () => () => {};

/**
 * False while React renders server HTML or hydrates it, true afterwards.
 *
 * Unlike a `mounted` flag set in a parent's effect, this is evaluated per component during
 * hydration (React uses the server snapshot), so a Suspense boundary that streams in and
 * hydrates *after* the shell (session/profile already known) still matches the server HTML.
 * That late-boundary case caused the intermittent React #418 on random admin pages.
 */
export function useHydrated(): boolean {
  return useSyncExternalStore(
    noopSubscribe,
    () => true,
    () => false
  );
}
