"use client";

import type { ReactNode } from "react";
import { GoogleMapsProvider } from "@porterchain/maps";
import { publicEnv } from "@/lib/env";

/** Scope Maps JS to routes that need Places/map UI — not the whole portal shell. */
export default function WithGoogleMaps({ children }: { children: ReactNode }) {
  return <GoogleMapsProvider apiKey={publicEnv.googleMapsApiKey}>{children}</GoogleMapsProvider>;
}
