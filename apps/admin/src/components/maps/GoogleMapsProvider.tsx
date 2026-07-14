"use client";

import type { ReactNode } from "react";
import { APIProvider } from "@vis.gl/react-google-maps";
import { getGoogleMapsApiKey, isGoogleMapsConfigured } from "@/lib/maps";

export default function GoogleMapsProvider({ children }: { children: ReactNode }) {
  if (!isGoogleMapsConfigured()) {
    return <>{children}</>;
  }
  return (
    <APIProvider
      apiKey={getGoogleMapsApiKey()}
      // drawing + visualization were removed from Maps JS API (May 2026) — load only supported libs.
      libraries={["places", "geometry", "marker"]}
      language="en"
      region="CA"
    >
      {children}
    </APIProvider>
  );
}
