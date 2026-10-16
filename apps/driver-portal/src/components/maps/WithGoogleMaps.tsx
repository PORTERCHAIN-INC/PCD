"use client";

import type { ReactNode } from "react";

/** Former Google Maps wrapper; MapLibre and /v1/geo need no provider. */
export default function WithGoogleMaps({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
