"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import GoogleMapsProvider from "@/components/maps/GoogleMapsProvider";
import MapCanvas from "@/components/live-map/MapCanvas";
import { useLiveMapData } from "@/hooks/useLiveMapData";
import { DEFAULT_LAYERS } from "@/lib/live-map";
import { isGoogleMapsConfigured } from "@/lib/maps";
import { Spinner } from "@/components/crm/primitives";
import { cn } from "@porterchain/ui/utils";

type Props = {
  theme?: "light" | "dark";
  className?: string;
};

export default function DashboardEmbeddedMap({ theme = "light", className }: Props) {
  const { data, error } = useLiveMapData();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const layers = useMemo(
    () => ({
      ...DEFAULT_LAYERS,
      heatMap: false,
      routes: false,
      cluster: true,
    }),
    []
  );

  if (!isGoogleMapsConfigured()) {
    return (
      <div className={cn("flex items-center justify-center rounded-xl bg-gray-bg text-sm text-muted", className)}>
        Configure Google Maps API key for live map
      </div>
    );
  }

  if (!data) {
    return (
      <div className={cn("flex items-center justify-center rounded-xl bg-gray-bg", className)}>
        <Spinner />
      </div>
    );
  }

  return (
    <div className={cn("relative overflow-hidden rounded-xl border border-primary/10", className)}>
      {error && (
        <p className="absolute left-2 top-2 z-10 rounded bg-amber-50 px-2 py-1 text-xs text-amber-800">
          {error}
        </p>
      )}
      <Link
        href="/live-map"
        className="absolute right-2 top-2 z-10 rounded-lg bg-white/90 px-2 py-1 text-xs font-medium text-secondary shadow"
      >
        Full map →
      </Link>
      <GoogleMapsProvider>
        <MapCanvas
          data={data}
          layers={layers}
          mapMode="roadmap"
          theme={theme}
          heatMetric="orders"
          selectedId={selectedId}
          onSelect={(_type, id) => setSelectedId(id)}
          measureActive={false}
          drawMode="none"
        />
      </GoogleMapsProvider>
    </div>
  );
}
