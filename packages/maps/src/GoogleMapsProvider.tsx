"use client";

import type { ReactNode } from "react";
import { APIProvider } from "@vis.gl/react-google-maps";
import { isGoogleMapsConfigured, resolveGoogleMapsApiKey } from "./maps-core";

export default function GoogleMapsProvider({
  children,
  apiKey,
}: {
  children: ReactNode;
  apiKey?: string;
}) {
  const key = resolveGoogleMapsApiKey(apiKey);
  if (!isGoogleMapsConfigured(key)) {
    return <>{children}</>;
  }

  return (
    <APIProvider apiKey={key} libraries={["places"]} language="en" region="CA">
      {children}
    </APIProvider>
  );
}
