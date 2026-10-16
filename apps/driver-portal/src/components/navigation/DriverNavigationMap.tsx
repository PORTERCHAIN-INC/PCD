"use client";

import {
  coordsFromAddress,
  decodePolyline,
  GTA_CENTER,
  resolveRoutePolylineEncoding,
} from "@/lib/navigation-map";
import type { DriverNavigationSession } from "@/lib/navigation";
import type { LatLng, MapCircle, MapLine, MapMarker } from "@porterchain/maps";
import dynamic from "next/dynamic";
import { useMemo } from "react";

const LibreMap = dynamic(() => import("@porterchain/maps/libre-map"), { ssr: false });

type Props = {
  session: DriverNavigationSession;
  deviceLocation?: LatLng | null;
  /** Live traffic is a Google-only layer; kept for API compatibility, no effect. */
  showTraffic?: boolean;
  replayIndex?: number;
  height?: string;
};

export function DriverNavigationMap({
  session,
  deviceLocation,
  replayIndex,
  height = "440px",
}: Props) {
  const pickup = coordsFromAddress(session.pickup);
  const dropoff = coordsFromAddress(session.dropoff);
  const driver = session.driver_location ?? session.current_location ?? deviceLocation;

  const pickupPath = useMemo(() => {
    const poly = session.pickup_route?.polyline;
    return poly ? decodePolyline(poly, resolveRoutePolylineEncoding(session.pickup_route)) : [];
  }, [session.pickup_route]);

  const deliveryPath = useMemo(() => {
    const route = session.delivery_route ?? session.optimized_route ?? session.eta;
    const poly = route?.polyline;
    return poly ? decodePolyline(poly, resolveRoutePolylineEncoding(route)) : [];
  }, [session.delivery_route, session.optimized_route, session.eta]);

  const replayFrames = useMemo(() => session.replay ?? [], [session.replay]);
  const replayPoint =
    replayIndex != null && replayFrames[replayIndex]
      ? { lat: replayFrames[replayIndex].lat, lng: replayFrames[replayIndex].lng }
      : null;

  const key = JSON.stringify([pickup, dropoff, driver, deviceLocation, replayPoint]);
  const fitPoints = useMemo(() => {
    const pts: LatLng[] = [];
    if (pickup) pts.push(pickup);
    if (dropoff) pts.push(dropoff);
    if (driver) pts.push(driver);
    if (deviceLocation) pts.push(deviceLocation);
    if (replayPoint) pts.push(replayPoint);
    return pts;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const markers = useMemo(() => {
    const m: MapMarker[] = [];
    if (pickup) m.push({ position: pickup, kind: "pickup", title: "Pickup" });
    if (dropoff) m.push({ position: dropoff, kind: "dropoff", title: "Delivery" });
    const d = replayPoint ?? driver;
    if (d) m.push({ position: d, kind: "driver-lg", title: "Driver" });
    if (deviceLocation) m.push({ position: deviceLocation, kind: "device", title: "Device GPS" });
    return m;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const lines = useMemo(() => {
    const l: MapLine[] = [];
    if (pickupPath.length > 1)
      l.push({ path: pickupPath, color: "#0ea5e9", width: 4, opacity: 0.85 });
    if (deliveryPath.length > 1)
      l.push({ path: deliveryPath, color: "#7c3aed", width: 4, opacity: 0.8 });
    if (replayFrames.length > 1)
      l.push({
        path: replayFrames.map((f) => ({ lat: f.lat, lng: f.lng })),
        color: "#94a3b8",
        width: 2,
        opacity: 0.55,
      });
    return l;
  }, [pickupPath, deliveryPath, replayFrames]);

  const circles = useMemo(() => {
    const c: MapCircle[] = [];
    for (const g of session.geofences ?? []) {
      const center = g.center as { lat: number; lng: number } | undefined;
      const radius = typeof g.radius_m === "number" ? g.radius_m : null;
      if (center?.lat != null && center?.lng != null && radius) {
        const type = String(g.geofence_type ?? "");
        const color = type === "pickup" ? "#16a34a" : type === "dropoff" ? "#dc2626" : "#2563eb";
        c.push({ center, radiusM: radius, color, strokeOpacity: 0.55 });
      }
    }
    return c;
  }, [session.geofences]);

  return (
    <div
      className="overflow-hidden rounded-2xl border border-[var(--primary)]/10 shadow-sm"
      style={{ height }}
    >
      <LibreMap
        center={driver ?? deviceLocation ?? dropoff ?? pickup ?? GTA_CENTER}
        markers={markers}
        lines={lines}
        circles={circles}
        fitPoints={fitPoints}
        minFitPoints={1}
        fitPadding={56}
      />
    </div>
  );
}
