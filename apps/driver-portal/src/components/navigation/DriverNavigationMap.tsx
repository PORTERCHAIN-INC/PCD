"use client";

import { coordsFromAddress, decodePolyline, GTA_CENTER } from "@/lib/navigation-map";
import type { DriverNavigationSession } from "@/lib/navigation";
import { AdvancedMarker, Map, Polyline, useMap, useMapsLibrary } from "@vis.gl/react-google-maps";
import { useEffect, useMemo, useRef } from "react";

type Props = {
  session: DriverNavigationSession;
  deviceLocation?: google.maps.LatLngLiteral | null;
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
        const type = String(g.geofence_type ?? "");
        const stroke = type === "pickup" ? "#16a34a" : type === "dropoff" ? "#dc2626" : "#2563eb";
        circlesRef.current.push(
          new google.maps.Circle({
            map,
            center,
            radius,
            strokeColor: stroke,
            strokeOpacity: 0.55,
            strokeWeight: 1,
            fillColor: stroke,
            fillOpacity: 0.08,
          })
        );
      }
    }

    return () => circlesRef.current.forEach((c) => c.setMap(null));
  }, [map, geofences]);

  return null;
}

function FitBounds({ points }: { points: google.maps.LatLngLiteral[] }) {
  const map = useMap();
  const boundsLib = useMapsLibrary("core");

  useEffect(() => {
    if (!map || !boundsLib || points.length < 1) return;
    const bounds = new google.maps.LatLngBounds();
    points.forEach((p) => bounds.extend(p));
    map.fitBounds(bounds, 56);
  }, [map, boundsLib, points]);

  return null;
}

export function DriverNavigationMap({
  session,
  deviceLocation,
  showTraffic = false,
  replayIndex,
  height = "440px",
}: Props) {
  const pickup = coordsFromAddress(session.pickup);
  const dropoff = coordsFromAddress(session.dropoff);
  const driver = session.driver_location ?? session.current_location ?? deviceLocation;

  const pickupPath = useMemo(() => {
    const poly = session.pickup_route?.polyline;
    return poly ? decodePolyline(poly) : [];
  }, [session.pickup_route?.polyline]);

  const deliveryPath = useMemo(() => {
    const poly =
      session.delivery_route?.polyline ??
      session.optimized_route?.polyline ??
      session.eta?.polyline;
    return poly ? decodePolyline(poly) : [];
  }, [
    session.delivery_route?.polyline,
    session.optimized_route?.polyline,
    session.eta?.polyline,
  ]);

  const replayFrames = session.replay ?? [];
  const replayPoint =
    replayIndex != null && replayFrames[replayIndex]
      ? { lat: replayFrames[replayIndex].lat, lng: replayFrames[replayIndex].lng }
      : null;

  const fitPoints = useMemo(() => {
    const pts: google.maps.LatLngLiteral[] = [];
    if (pickup) pts.push(pickup);
    if (dropoff) pts.push(dropoff);
    if (driver) pts.push(driver);
    if (deviceLocation) pts.push(deviceLocation);
    if (replayPoint) pts.push(replayPoint);
    return pts;
  }, [pickup, dropoff, driver, deviceLocation, replayPoint]);

  const center = driver ?? deviceLocation ?? dropoff ?? pickup ?? GTA_CENTER;

  return (
    <div
      className="overflow-hidden rounded-2xl border border-[var(--primary)]/10 shadow-sm"
      style={{ height }}
    >
      <Map
        defaultCenter={center}
        defaultZoom={12}
        gestureHandling="greedy"
        disableDefaultUI={false}
        mapId="driver-navigation"
      >
        <TrafficLayer enabled={showTraffic} />
        <GeofenceCircles geofences={session.geofences ?? []} />
        {fitPoints.length >= 1 && <FitBounds points={fitPoints} />}

        {pickup && (
          <AdvancedMarker position={pickup} title="Pickup">
            <div className="rounded-full bg-green-600 px-2 py-0.5 text-[10px] font-bold text-white shadow">
              P
            </div>
          </AdvancedMarker>
        )}
        {dropoff && (
          <AdvancedMarker position={dropoff} title="Delivery">
            <div className="rounded-full bg-red-600 px-2 py-0.5 text-[10px] font-bold text-white shadow">
              D
            </div>
          </AdvancedMarker>
        )}
        {(replayPoint || driver) && (
          <AdvancedMarker position={replayPoint ?? driver!} title="Driver">
            <div className="h-4 w-4 rounded-full border-2 border-white bg-blue-600 shadow-lg" />
          </AdvancedMarker>
        )}
        {deviceLocation && (
          <AdvancedMarker position={deviceLocation} title="Device GPS">
            <div className="h-2.5 w-2.5 rounded-full border border-white bg-sky-400 shadow" />
          </AdvancedMarker>
        )}

        {pickupPath.length > 1 && (
          <Polyline path={pickupPath} strokeColor="#0ea5e9" strokeWeight={4} strokeOpacity={0.85} />
        )}
        {deliveryPath.length > 1 && (
          <Polyline path={deliveryPath} strokeColor="#7c3aed" strokeWeight={4} strokeOpacity={0.8} />
        )}
        {replayFrames.length > 1 && (
          <Polyline
            path={replayFrames.map((f) => ({ lat: f.lat, lng: f.lng }))}
            strokeColor="#94a3b8"
            strokeWeight={2}
            strokeOpacity={0.55}
          />
        )}
      </Map>
    </div>
  );
}
