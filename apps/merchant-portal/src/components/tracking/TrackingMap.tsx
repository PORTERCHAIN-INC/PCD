"use client";

import {
  coordsFromAddress,
  decodePolyline,
  GTA_CENTER,
  resolveRoutePolylineEncoding,
} from "@/lib/tracking-map";
import type { LiveTracking } from "@/lib/tracking";
import { MapShell } from "@/components/tracking/MapShell";
import type { LatLng, MapCircle, MapLine, MapMarker } from "@porterchain/maps";
import dynamic from "next/dynamic";
import { useMemo } from "react";

const LibreMap = dynamic(() => import("@porterchain/maps/libre-map"), { ssr: false });

type Props = {
  tracking: LiveTracking;
  /** Live traffic is a Google-only layer; kept for API compatibility, no effect. */
  showTraffic?: boolean;
  replayIndex?: number;
  height?: string;
};

export function TrackingMap({ tracking, replayIndex, height = "420px" }: Props) {
  const pickup = coordsFromAddress(tracking.pickup);
  const dropoff = coordsFromAddress(tracking.dropoff);
  const driver = tracking.driver_location;

  const optimizedPath = useMemo(() => {
    const poly = tracking.optimized_route?.polyline;
    return poly ? decodePolyline(poly, resolveRoutePolylineEncoding(tracking.optimized_route)) : [];
  }, [tracking.optimized_route]);

  const etaPath = useMemo(() => {
    const poly = tracking.eta?.polyline;
    return poly ? decodePolyline(poly, resolveRoutePolylineEncoding(tracking.eta)) : [];
  }, [tracking.eta]);

  const replayFrames = useMemo(() => tracking.replay ?? [], [tracking.replay]);
  const replayPoint =
    replayIndex != null && replayFrames[replayIndex]
      ? { lat: replayFrames[replayIndex].lat, lng: replayFrames[replayIndex].lng }
      : null;

  const key = JSON.stringify([pickup, dropoff, driver, replayPoint]);
  const fitPoints = useMemo(() => {
    const pts: LatLng[] = [];
    if (pickup) pts.push(pickup);
    if (dropoff) pts.push(dropoff);
    if (driver) pts.push(driver);
    if (replayPoint) pts.push(replayPoint);
    return pts;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const markers = useMemo(() => {
    const m: MapMarker[] = [];
    if (pickup) m.push({ position: pickup, kind: "pickup", title: "Pickup" });
    if (dropoff) m.push({ position: dropoff, kind: "dropoff", title: "Dropoff" });
    const d = replayPoint ?? driver;
    if (d) m.push({ position: d, kind: "driver", title: "Driver" });
    return m;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const lines = useMemo(() => {
    const l: MapLine[] = [];
    if (optimizedPath.length > 1)
      l.push({ path: optimizedPath, color: "#7c3aed", width: 4, opacity: 0.8 });
    if (etaPath.length > 1) l.push({ path: etaPath, color: "#0ea5e9", width: 3, opacity: 0.7 });
    if (replayFrames.length > 1)
      l.push({
        path: replayFrames.map((f) => ({ lat: f.lat, lng: f.lng })),
        color: "#94a3b8",
        width: 2,
        opacity: 0.5,
      });
    return l;
  }, [optimizedPath, etaPath, replayFrames]);

  const circles = useMemo(() => {
    const c: MapCircle[] = [];
    for (const g of tracking.geofences ?? []) {
      const center = g.center as { lat: number; lng: number } | undefined;
      const radius = typeof g.radius_m === "number" ? g.radius_m : null;
      if (center?.lat != null && center?.lng != null && radius)
        c.push({ center, radiusM: radius, color: "#2563eb", strokeOpacity: 0.5 });
    }
    return c;
  }, [tracking.geofences]);

  return (
    <MapShell height={height}>
      <div className="overflow-hidden rounded-2xl border border-primary/10" style={{ height }}>
        <LibreMap
          center={driver ?? dropoff ?? pickup ?? GTA_CENTER}
          markers={markers}
          lines={lines}
          circles={circles}
          fitPoints={fitPoints}
          fitPadding={48}
        />
      </div>
    </MapShell>
  );
}
