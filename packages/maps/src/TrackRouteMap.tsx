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

  if (!isGoogleMapsConfigured()) {
    return (
      <div
        className={`rounded-2xl border border-primary/10 bg-gray-bg flex items-center justify-center text-sm text-muted ${className}`}
        style={{ height }}
      >
        Map unavailable — configure Google Maps API key
      </div>
    );
  }

  if (!pickupPt && !dropoffPt) {
    return (
      <div
        className={`rounded-2xl border border-primary/10 bg-gray-bg flex items-center justify-center text-sm text-muted ${className}`}
        style={{ height }}
      >
        Route map will appear when pickup and drop-off coordinates are available
      </div>
    );
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
