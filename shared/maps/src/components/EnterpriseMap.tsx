"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { View, StyleSheet, type ViewStyle } from "react-native";
import MapView, { Marker, PROVIDER_GOOGLE } from "react-native-maps";
import { useMapsConfig } from "../MapsProvider";
import type { EnterpriseMapSession } from "../session";
import { buildEntitiesFromSession, EntityMarkers } from "./EntityMarkers";
import { GeofenceLayer } from "./GeofenceLayer";
import { RouteLayers } from "./RouteLayers";
import { HeatmapLayer } from "./HeatmapLayer";
import { EtaBadge } from "./EtaBadge";
import { RouteReplayControls, replayMarkerCoordinate } from "./RouteReplayControls";
import { coordsFromAddress, fitRegion, replayToLatLng, toLatLng } from "../geo";
import { verifyRoutingEngines } from "../verify";
import { DEFAULT_REGION } from "../types";

export type EnterpriseMapProps = {
  session: EnterpriseMapSession;
  height?: number;
  style?: ViewStyle;
  showTraffic?: boolean;
  showHeatmap?: boolean;
  showGeofences?: boolean;
  showReplayControls?: boolean;
  replayIndex?: number | null;
  onReplayIndexChange?: (index: number | null) => void;
};

/**
 * Enterprise map — Google Maps renders only.
 * Tracking, ETA, and routes come from Porterchain API (Fleetbase / OSRM / Valhalla).
 */
export function EnterpriseMap({
  session,
  height = 360,
  style,
  showTraffic = true,
  showHeatmap = false,
  showGeofences = true,
  showReplayControls = false,
  replayIndex: controlledReplayIndex,
  onReplayIndexChange,
}: EnterpriseMapProps) {
  const { enabled } = useMapsConfig();
  const mapRef = useRef<MapView>(null);
  const [internalReplayIndex, setInternalReplayIndex] = useState<number | null>(null);
  const replayIndex =
    controlledReplayIndex !== undefined ? controlledReplayIndex : internalReplayIndex;

  useEffect(() => {
    if (__DEV__) {
      const check = verifyRoutingEngines(session.routing_engines);
      if (!check.valid) {
        console.warn("[EnterpriseMap] routing engine mismatch:", check.violations);
      }
    }
  }, [session.routing_engines]);

  const entities = useMemo(() => buildEntitiesFromSession(session), [session]);

  const replayPath = useMemo(() => replayToLatLng(session.replay ?? []), [session.replay]);
  const replayMarker = replayMarkerCoordinate(session.replay ?? [], replayIndex);

  const fitPoints = useMemo(() => {
    const pts = entities.map((e) => toLatLng(e.coordinate)).filter(Boolean) as Array<{
      latitude: number;
      longitude: number;
    }>;
    if (replayMarker) pts.push(replayMarker);
    replayPath.forEach((p) => pts.push(p));
    return pts;
  }, [entities, replayMarker, replayPath]);

  const initialRegion = useMemo(
    () => (fitPoints.length > 0 ? fitRegion(fitPoints) : DEFAULT_REGION),
    [fitPoints]
  );

  useEffect(() => {
    if (fitPoints.length > 1 && mapRef.current) {
      mapRef.current.fitToCoordinates(fitPoints, {
        edgePadding: { top: 48, right: 48, bottom: 48, left: 48 },
        animated: true,
      });
    }
  }, [fitPoints]);

  if (!enabled) {
    return (
      <View style={[styles.placeholder, { height }, style]}>
        <View style={styles.placeholderInner}>
          <EtaBadge
            eta={session.eta}
            gpsSource={session.gps_source}
            engines={session.routing_engines}
          />
        </View>
      </View>
    );
  }

  const driverCoord =
    replayMarker ??
    toLatLng(session.driver_location) ??
    toLatLng(session.current_location) ??
    coordsFromAddress(session.pickup);

  return (
    <View style={[{ height, borderRadius: 16, overflow: "hidden" }, style]}>
      <MapView
        ref={mapRef}
        style={StyleSheet.absoluteFill}
        provider={PROVIDER_GOOGLE}
        initialRegion={initialRegion}
        showsUserLocation={Boolean(session.device_location)}
        showsTraffic={showTraffic && (session.traffic?.layer_available ?? true)}
        showsCompass
        showsScale
      >
        <EntityMarkers entities={entities.filter((e) => e.kind !== "driver")} />
        {driverCoord ? (
          <Marker coordinate={driverCoord} title="Driver" zIndex={99}>
            <View style={styles.driverDot} />
          </Marker>
        ) : null}

        {showGeofences && session.geofences?.length ? (
          <GeofenceLayer geofences={session.geofences} />
        ) : null}

        <RouteLayers
          pickupRoute={session.pickup_route}
          deliveryRoute={session.delivery_route}
          optimizedRoute={session.optimized_route}
          etaRoute={session.eta}
          fleetbasePolyline={session.route_polyline}
          replayPath={replayPath}
        />

        {showHeatmap && session.heatmap?.length ? <HeatmapLayer points={session.heatmap} /> : null}
      </MapView>

      <View style={styles.etaOverlay} pointerEvents="none">
        <EtaBadge
          eta={session.eta}
          gpsSource={session.gps_source}
          engines={session.routing_engines}
        />
      </View>

      {showReplayControls ? (
        <View style={styles.replayOverlay}>
          <RouteReplayControls
            frames={session.replay ?? []}
            onIndexChange={(i) => {
              setInternalReplayIndex(i);
              onReplayIndexChange?.(i);
            }}
          />
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  placeholder: {
    backgroundColor: "#e2e8f0",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 16,
  },
  placeholderInner: { padding: 16 },
  etaOverlay: {
    position: "absolute",
    top: 12,
    left: 12,
    right: 12,
  },
  replayOverlay: {
    position: "absolute",
    bottom: 12,
    left: 12,
    right: 12,
  },
  driverDot: {
    width: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: "#2563eb",
    borderWidth: 2,
    borderColor: "#fff",
  },
});
