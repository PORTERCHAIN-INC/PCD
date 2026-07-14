"use client";

import {
  coordsFromAddress,
  decodePolyline,
  GTA_CENTER,
  resolveRoutePolylineEncoding,
} from "@/lib/tracking-map";
import type { LiveTracking } from "@/lib/tracking";
import { MapShell } from "@/components/tracking/MapShell";
import { AdvancedMarker, Map, Polyline, useMap, useMapsLibrary } from "@vis.gl/react-google-maps";
import { useEffect, useMemo, useRef } from "react";

type Props = {
  tracking: LiveTracking;
  showTraffic?: boolean;
  replayIndex?: number;
  height?: string;
};

function TrafficLayer({ enabled }: { enabled: boolean }) {
  const map = useMap();
  const layerRef = useRef<google.maps.TrafficLayer | null>(null);

  useEffect(() => {
    if (!map) return;
    if (enabled) {
      layerRef.current = layerRef.current ?? new google.maps.TrafficLayer();
      layerRef.current.setMap(map);
    } else {
      layerRef.current?.setMap(null);
    }
  }, [map, enabled]);

  return null;
}

function GeofenceCircles({ geofences }: { geofences: Array<Record<string, unknown>> }) {
  const map = useMap();
  const circlesRef = useRef<google.maps.Circle[]>([]);

  useEffect(() => {
    if (!map) return;
    circlesRef.current.forEach((c) => c.setMap(null));
    circlesRef.current = [];

    for (const g of geofences) {
      const center = g.center as { lat: number; lng: number } | undefined;
      const radius = typeof g.radius_m === "number" ? g.radius_m : null;
      if (center?.lat != null && center?.lng != null && radius) {
        const circle = new google.maps.Circle({
          map,
          center,
          radius,
          strokeColor: "#2563eb",
          strokeOpacity: 0.5,
          strokeWeight: 1,
          fillColor: "#3b82f6",
          fillOpacity: 0.08,
        });
        circlesRef.current.push(circle);
      }
    }

    return () => {
      circlesRef.current.forEach((c) => c.setMap(null));
    };
  }, [map, geofences]);

  return null;
}

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

export function TrackingMap({
  tracking,
  showTraffic = false,
  replayIndex,
  height = "420px",
}: Props) {
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

  const replayFrames = tracking.replay ?? [];
  const replayPoint =
    replayIndex != null && replayFrames[replayIndex]
      ? { lat: replayFrames[replayIndex].lat, lng: replayFrames[replayIndex].lng }
      : null;

  const fitPoints = useMemo(() => {
    const pts: google.maps.LatLngLiteral[] = [];
    if (pickup) pts.push(pickup);
    if (dropoff) pts.push(dropoff);
    if (driver) pts.push(driver);
    if (replayPoint) pts.push(replayPoint);
    return pts;
  }, [pickup, dropoff, driver, replayPoint]);

  const center = driver ?? dropoff ?? pickup ?? GTA_CENTER;

  return (
    <MapShell height={height}>
      <div className="overflow-hidden rounded-2xl border border-primary/10" style={{ height }}>
        <Map
          defaultCenter={center}
          defaultZoom={12}
          gestureHandling="greedy"
          disableDefaultUI={false}
          mapId="merchant-tracking"
        >
          <TrafficLayer enabled={showTraffic} />
          <GeofenceCircles geofences={tracking.geofences ?? []} />
          {fitPoints.length >= 2 && <FitBounds points={fitPoints} />}

          {pickup && (
            <AdvancedMarker position={pickup} title="Pickup">
              <div className="rounded-full bg-green-600 px-2 py-0.5 text-[10px] font-bold text-white">
                P
              </div>
            </AdvancedMarker>
          )}
          {dropoff && (
            <AdvancedMarker position={dropoff} title="Dropoff">
              <div className="rounded-full bg-red-600 px-2 py-0.5 text-[10px] font-bold text-white">
                D
              </div>
            </AdvancedMarker>
          )}
          {(replayPoint || driver) && (
            <AdvancedMarker position={replayPoint ?? driver!} title="Driver">
              <div className="h-3 w-3 rounded-full border-2 border-white bg-blue-600 shadow" />
            </AdvancedMarker>
          )}

          {optimizedPath.length > 1 && (
            <Polyline
              path={optimizedPath}
              strokeColor="#7c3aed"
              strokeWeight={4}
              strokeOpacity={0.8}
            />
          )}
          {etaPath.length > 1 && (
            <Polyline path={etaPath} strokeColor="#0ea5e9" strokeWeight={3} strokeOpacity={0.7} />
          )}
          {replayFrames.length > 1 && (
            <Polyline
              path={replayFrames.map((f) => ({ lat: f.lat, lng: f.lng }))}
              strokeColor="#94a3b8"
              strokeWeight={2}
              strokeOpacity={0.5}
            />
          )}
        </Map>
      </div>
    </MapShell>
  );
}
