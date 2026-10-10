/// <reference types="google.maps" />
"use client";

import { AdvancedMarker, Map, Polyline, useMap, useMapsLibrary } from "@vis.gl/react-google-maps";
import { useEffect, useMemo } from "react";
import { GTA_CENTER, coordsFromAddress, isGoogleMapsConfigured } from "./maps-core";
import { decodePolyline } from "./polyline";

export type TrackRouteMapProps = {
  pickup?: Record<string, unknown> | null;
  dropoff?: Record<string, unknown> | null;
  driverLocation?: { lat: number; lng: number } | null;
  routePolyline?: string | null;
  routePolylineEncoding?: "google" | "valhalla";
  height?: string;
  className?: string;
};

function FitBounds({ points }: { points: google.maps.LatLngLiteral[] }) {
  const map = useMap();
  const boundsLib = useMapsLibrary("core");

  useEffect(() => {
    if (!map || !boundsLib || points.length < 2) return;
    const bounds = new google.maps.LatLngBounds();
    points.forEach((p) => bounds.extend(p));
    map.fitBounds(bounds, 48);
  }, [map, boundsLib, points]);

  return null;
}

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
    const pts: google.maps.LatLngLiteral[] = [];
    if (pickupPt) pts.push(pickupPt);
    if (dropoffPt) pts.push(dropoffPt);
    if (driverLocation) pts.push(driverLocation);
    return pts;
  }, [pickupPt, dropoffPt, driverLocation]);

  const center = driverLocation ?? dropoffPt ?? pickupPt ?? GTA_CENTER;

  // No key or no coordinates yet: a clean route card, never an engineering message.
  if (!isGoogleMapsConfigured() || (!pickupPt && !dropoffPt)) {
    return <RouteCard pickup={pickup} dropoff={dropoff} height={height} className={className} />;
  }

  return (
    <div
      className={`overflow-hidden rounded-2xl border border-primary/10 ${className}`}
      style={{ height }}
    >
      <Map
        defaultCenter={center}
        defaultZoom={12}
        gestureHandling="cooperative"
        disableDefaultUI={false}
        mapId="porterchain-track"
        style={{ width: "100%", height: "100%" }}
      >
        {fitPoints.length >= 2 && <FitBounds points={fitPoints} />}
        {pickupPt && (
          <AdvancedMarker position={pickupPt} title="Pickup">
            <div className="rounded-full bg-green-600 px-2 py-0.5 text-[10px] font-bold text-white">
              P
            </div>
          </AdvancedMarker>
        )}
        {dropoffPt && (
          <AdvancedMarker position={dropoffPt} title="Drop-off">
            <div className="rounded-full bg-red-600 px-2 py-0.5 text-[10px] font-bold text-white">
              D
            </div>
          </AdvancedMarker>
        )}
        {driverLocation && (
          <AdvancedMarker position={driverLocation} title="Driver">
            <div className="h-3 w-3 rounded-full border-2 border-white bg-blue-600 shadow" />
          </AdvancedMarker>
        )}
        {routePath.length > 1 && (
          <Polyline path={routePath} strokeColor="#2563eb" strokeWeight={4} strokeOpacity={0.85} />
        )}
      </Map>
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
