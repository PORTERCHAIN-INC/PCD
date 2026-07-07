"use client";

import { Circle, Polyline } from "react-native-maps";
import type { MapGeofence } from "../session";

const STROKE: Record<string, string> = {
  pickup: "#16a34a",
  dropoff: "#dc2626",
  warehouse: "#d97706",
  delivery_zone: "#2563eb",
};

export function GeofenceLayer({ geofences }: { geofences: MapGeofence[] }) {
  return (
    <>
      {geofences.map((g) => {
        const stroke = STROKE[g.geofence_type] ?? "#2563eb";
        return (
          <Circle
            key={g.id}
            center={{ latitude: g.center.lat, longitude: g.center.lng }}
            radius={g.radius_m}
            strokeColor={stroke}
            strokeWidth={1}
            fillColor={`${stroke}22`}
          />
        );
      })}
    </>
  );
}
