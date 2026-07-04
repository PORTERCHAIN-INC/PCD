"use client";

import { View, Text, StyleSheet } from "react-native";
import { Marker } from "react-native-maps";
import type { MapEntity } from "../session";
import { toLatLng } from "../geo";

const COLORS: Record<MapEntity["kind"], string> = {
  driver: "#2563eb",
  customer: "#059669",
  merchant: "#7c3aed",
  warehouse: "#d97706",
  pickup: "#16a34a",
  dropoff: "#dc2626",
  device: "#38bdf8",
};

const LABELS: Record<MapEntity["kind"], string> = {
  driver: "D",
  customer: "C",
  merchant: "M",
  warehouse: "W",
  pickup: "P",
  dropoff: "D",
  device: "•",
};

export function buildEntitiesFromSession(session: {
  pickup?: Record<string, unknown> | null;
  dropoff?: Record<string, unknown> | null;
  merchant?: Record<string, unknown> | null;
  warehouse?: Record<string, unknown> | null;
  driver_location?: { lat: number; lng: number } | null;
  customer_location?: { lat: number; lng: number } | null;
  device_location?: { lat: number; lng: number } | null;
}): MapEntity[] {
  const entities: MapEntity[] = [];
  const add = (
    kind: MapEntity["kind"],
    coord: { lat: number; lng: number } | null,
    title?: string
  ) => {
    if (!coord) return;
    entities.push({ id: kind, kind, coordinate: coord, title });
  };

  const pickup = session.pickup;
  const dropoff = session.dropoff;
  if (pickup?.lat != null && pickup?.lng != null)
    add("pickup", { lat: Number(pickup.lat), lng: Number(pickup.lng) }, "Pickup");
  if (dropoff?.lat != null && dropoff?.lng != null)
    add("dropoff", { lat: Number(dropoff.lat), lng: Number(dropoff.lng) }, "Dropoff");
  if (session.merchant?.lat != null && session.merchant?.lng != null) {
    add(
      "merchant",
      { lat: Number(session.merchant.lat), lng: Number(session.merchant.lng) },
      "Merchant"
    );
  }
  if (session.warehouse?.lat != null && session.warehouse?.lng != null) {
    add(
      "warehouse",
      { lat: Number(session.warehouse.lat), lng: Number(session.warehouse.lng) },
      "Warehouse"
    );
  }
  add("driver", session.driver_location ?? null, "Driver");
  add("customer", session.customer_location ?? null, "Customer");
  add("device", session.device_location ?? null, "Device GPS");

  return entities;
}

export function EntityMarkers({ entities }: { entities: MapEntity[] }) {
  return (
    <>
      {entities.map((entity) => {
        const coord = toLatLng(entity.coordinate);
        if (!coord) return null;
        const color = COLORS[entity.kind];
        const label = LABELS[entity.kind];
        return (
          <Marker
            key={`${entity.kind}-${entity.id}`}
            coordinate={coord}
            title={entity.title ?? entity.kind}
          >
            <View
              style={[
                styles.pin,
                { backgroundColor: color },
                entity.kind === "driver" && styles.driverPin,
              ]}
            >
              <Text style={styles.pinText}>{label}</Text>
            </View>
          </Marker>
        );
      })}
    </>
  );
}

const styles = StyleSheet.create({
  pin: {
    minWidth: 22,
    height: 22,
    borderRadius: 11,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 2,
    borderColor: "#fff",
    paddingHorizontal: 4,
  },
  driverPin: {
    width: 18,
    height: 18,
    borderRadius: 9,
    minWidth: 18,
  },
  pinText: {
    color: "#fff",
    fontSize: 10,
    fontWeight: "700",
  },
});
