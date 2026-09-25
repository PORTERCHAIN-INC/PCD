"use client";

import type { ReactNode } from "react";
import { GoogleMapsProvider } from "@porterchain/maps";
import { publicEnv } from "@/lib/env";

/** Maps only on navigation — not the whole driver shell. */
export default function WithGoogleMaps({ children }: { children: ReactNode }) {
  return <GoogleMapsProvider apiKey={publicEnv.googleMapsApiKey}>{children}</GoogleMapsProvider>;
}
