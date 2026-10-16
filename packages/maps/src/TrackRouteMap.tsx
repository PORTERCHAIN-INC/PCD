"use client";

import dynamic from "next/dynamic";
import { useMemo } from "react";
import { coordsFromAddress } from "./maps-core";
import { decodePolyline } from "./polyline";
import type { LatLng } from "./types";
import type { MapMarker } from "./LibreMap";

const LibreMap = dynamic(() => import("./LibreMap"), { ssr: false });

export type TrackRouteMapProps = {
  pickup?: Record<string, unknown> | null;
  dropoff?: Record<string, unknown> | null;
  driverLocation?: { lat: number; lng: number } | null;
  routePolyline?: string | null;
  routePolylineEncoding?: "google" | "valhalla";
  height?: string;
  className?: string;
};

export default function TrackRouteMap({
  pickup,
  dropoff,
  driverLocation,
  routePolyline,
  routePolylineEncoding = "google",
  height = "280px",
  className = "",
}: TrackRouteMapProps) {
  const pickupPt = coordsFromAddress(pickup);
  const dropoffPt = coordsFromAddress(dropoff);
  const routePath = useMemo(
    () => (routePolyline ? decodePolyline(routePolyline, routePolylineEncoding) : []),
    [routePolyline, routePolylineEncoding]
  );

  const fitPoints = useMemo(() => {
    const pts: LatLng[] = [];
    if (pickupPt) pts.push(pickupPt);
    if (dropoffPt) pts.push(dropoffPt);
    if (driverLocation) pts.push(driverLocation);
    return pts;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify([pickupPt, dropoffPt, driverLocation])]);

  const markers = useMemo(() => {
    const m: MapMarker[] = [];
    if (pickupPt) m.push({ position: pickupPt, kind: "pickup", title: "Pickup" });
    if (dropoffPt) m.push({ position: dropoffPt, kind: "dropoff", title: "Drop-off" });
    if (driverLocation) m.push({ position: driverLocation, kind: "driver", title: "Driver" });
    return m;
  }, [fitPoints]); // eslint-disable-line react-hooks/exhaustive-deps

  const lines = useMemo(
    () =>
      routePath.length > 1 ? [{ path: routePath, color: "#2563eb", width: 4, opacity: 0.85 }] : [],
    [routePath]
  );

  // No coordinates yet: a clean route card, never an engineering message.
  if (!pickupPt && !dropoffPt) {
    return <RouteCard pickup={pickup} dropoff={dropoff} height={height} className={className} />;
  }

  return (
    <div
      className={`overflow-hidden rounded-2xl border border-primary/10 ${className}`}
      style={{ height }}
    >
      <LibreMap
        center={driverLocation ?? dropoffPt ?? pickupPt ?? undefined}
        markers={markers}
        lines={lines}
        fitPoints={fitPoints}
        gestureHandling="cooperative"
      />
    </div>
  );
}

function areaLabel(addr?: Record<string, unknown> | null): string {
  if (!addr) return "";
  const formatted = typeof addr.formatted === "string" ? addr.formatted : "";
  const postal = typeof addr.postal === "string" ? addr.postal : "";
  const match = (postal || formatted).toUpperCase().match(/[A-Z]\d[A-Z]\s?\d[A-Z]\d|[A-Z]\d[A-Z]/);
  const city = typeof addr.city === "string" ? addr.city : "";
  const street = formatted.split(",")[0]?.trim() ?? "";
  return [street, city, match?.[0]?.slice(0, 3)].filter(Boolean).slice(0, 2).join(" · ") || "—";
}

/** Static route summary used when a live map cannot be drawn. AA contrast, no jargon. */
export function RouteCard({
  pickup,
  dropoff,
  height,
  className = "",
}: {
  pickup?: Record<string, unknown> | null;
  dropoff?: Record<string, unknown> | null;
  height?: string;
  className?: string;
}) {
  return (
    <div
      data-testid="route-card"
      className={`flex flex-col justify-center rounded-2xl border border-primary/10 bg-white px-5 py-6 ${className}`}
      style={{ minHeight: height ? `min(${height}, 200px)` : undefined }}
    >
      <ol className="relative space-y-6 pl-7">
        <span aria-hidden className="absolute bottom-3 left-[7px] top-3 w-px bg-primary/20" />
        <li className="relative">
          <span
            aria-hidden
            className="absolute -left-7 top-1 h-3.5 w-3.5 rounded-full border-2 border-primary bg-white"
          />
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary/70">
            Pickup
          </p>
          <p className="mt-0.5 text-base font-semibold text-primary">{areaLabel(pickup)}</p>
        </li>
        <li className="relative">
          <span
            aria-hidden
            className="absolute -left-7 top-1 h-3.5 w-3.5 rounded-full bg-primary"
          />
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary/70">
            Drop-off
          </p>
          <p className="mt-0.5 text-base font-semibold text-primary">{areaLabel(dropoff)}</p>
        </li>
      </ol>
    </div>
  );
}
