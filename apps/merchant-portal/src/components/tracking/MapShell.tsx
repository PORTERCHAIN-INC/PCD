"use client";

import type { ReactNode } from "react";

/** Wrapper kept for layout parity; maps need no key or auth check now (MapLibre + our tiles). */
export function MapShell({ children }: { children: ReactNode; height: string }) {
  return <>{children}</>;
}
