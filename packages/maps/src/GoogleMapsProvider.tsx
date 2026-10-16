"use client";

import type { ReactNode } from "react";

/**
 * Former Google Maps API provider. Maps (MapLibre) and address search
 * (/v1/geo) need no key or context now, so this is a pass-through kept so
 * existing wrappers keep compiling.
 */
export default function MapsProvider({ children }: { children: ReactNode; apiKey?: string }) {
  return <>{children}</>;
}
