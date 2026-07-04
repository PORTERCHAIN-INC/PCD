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
      libraries={["places", "drawing", "geometry", "visualization", "marker"]}
      language="en"
      region="CA"
    >
      {children}
    </APIProvider>
  );
}
