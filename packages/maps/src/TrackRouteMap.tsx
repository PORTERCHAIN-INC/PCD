/// <reference types="google.maps" />
"use client";

import { AdvancedMarker, Map, Polyline, useMap, useMapsLibrary } from "@vis.gl/react-google-maps";
import { useEffect, useMemo } from "react";
import { GTA_CENTER, coordsFromAddress, isGoogleMapsConfigured } from "./maps-core";

export type TrackRouteMapProps = {
  pickup?: Record<string, unknown> | null;
  dropoff?: Record<string, unknown> | null;
  driverLocation?: { lat: number; lng: number } | null;
  routePolyline?: string | null;
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

function decodePolyline(encoded: string): google.maps.LatLngLiteral[] {
  const points: google.maps.LatLngLiteral[] = [];
  let index = 0;
  let lat = 0;
  let lng = 0;

  while (index < encoded.length) {
    let shift = 0;
    let result = 0;
    let byte: number;
    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);
    lat += result & 1 ? ~(result >> 1) : result >> 1;

    shift = 0;
    result = 0;
    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);
    lng += result & 1 ? ~(result >> 1) : result >> 1;

    points.push({ lat: lat / 1e5, lng: lng / 1e5 });
  }
  return points;
}

export default function TrackRouteMap({
  pickup,
  dropoff,
  driverLocation,
  routePolyline,
  height = "280px",
  className = "",
}: TrackRouteMapProps) {
  const pickupPt = coordsFromAddress(pickup);
  const dropoffPt = coordsFromAddress(dropoff);
  const routePath = useMemo(
    () => (routePolyline ? decodePolyline(routePolyline) : []),
    [routePolyline]
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
