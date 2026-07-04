"use client";

import { Polyline } from "react-native-maps";
import { decodeRoutePolyline } from "../geo";
import type { RouteLeg } from "../session";

type RouteLayersProps = {
  pickupRoute?: RouteLeg | null;
  deliveryRoute?: RouteLeg | null;
  optimizedRoute?: RouteLeg | null;
  etaRoute?: RouteLeg | null;
  fleetbasePolyline?: string | null;
  replayPath?: Array<{ latitude: number; longitude: number }>;
};

export function RouteLayers({
  pickupRoute,
  deliveryRoute,
  optimizedRoute,
  etaRoute,
  fleetbasePolyline,
  replayPath,
}: RouteLayersProps) {
  const pickupPath = pickupRoute?.polyline
    ? decodeRoutePolyline(pickupRoute.polyline, pickupRoute.source)
    : [];
  const deliveryPath = deliveryRoute?.polyline
    ? decodeRoutePolyline(deliveryRoute.polyline, deliveryRoute.source)
    : [];
  const optimizedPath = optimizedRoute?.polyline
    ? decodeRoutePolyline(optimizedRoute.polyline, optimizedRoute.source)
    : [];
  const etaPath = etaRoute?.polyline ? decodeRoutePolyline(etaRoute.polyline, etaRoute.source) : [];
  const fleetPath = fleetbasePolyline ? decodeRoutePolyline(fleetbasePolyline, "osrm") : [];

  const primary =
    optimizedPath.length > 1
      ? optimizedPath
      : deliveryPath.length > 1
        ? deliveryPath
        : etaPath.length > 1
          ? etaPath
          : fleetPath;

  return (
    <>
      {pickupPath.length > 1 ? (
        <Polyline coordinates={pickupPath} strokeColor="#0ea5e9" strokeWidth={4} lineCap="round" lineJoin="round" />
      ) : null}
      {primary.length > 1 ? (
        <Polyline coordinates={primary} strokeColor="#7c3aed" strokeWidth={4} lineCap="round" lineJoin="round" />
      ) : null}
      {etaPath.length > 1 && etaPath !== primary ? (
        <Polyline coordinates={etaPath} strokeColor="#2563eb" strokeWidth={3} lineDashPattern={[6, 4]} />
      ) : null}
      {replayPath && replayPath.length > 1 ? (
        <Polyline coordinates={replayPath} strokeColor="#94a3b8" strokeWidth={2} lineDashPattern={[4, 6]} />
      ) : null}
    </>
  );
}
