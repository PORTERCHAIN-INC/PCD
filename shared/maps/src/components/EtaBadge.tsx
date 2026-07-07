"use client";

import { View, Text, StyleSheet } from "react-native";
import { formatDistance, formatEta } from "../geo";
import type { RouteLeg } from "../session";

export function EtaBadge({
  eta,
  gpsSource,
  engines,
}: {
  eta?: RouteLeg | null;
  gpsSource?: string | null;
  engines?: { gps?: string; eta?: string; optimized_route?: string };
}) {
  if (!eta) return null;

  return (
    <View style={styles.wrap}>
      <Text style={styles.title}>ETA {eta.eta_label ?? formatEta(eta.duration_seconds)}</Text>
      <Text style={styles.meta}>
        {formatDistance(eta.distance_meters)} · {eta.source ?? engines?.eta ?? "osrm"} · GPS{" "}
        {gpsSource ?? engines?.gps ?? "fleetbase"}
      </Text>
      {engines?.optimized_route ? (
        <Text style={styles.meta}>Route {engines.optimized_route}</Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    backgroundColor: "rgba(10, 22, 40, 0.88)",
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 12,
    gap: 2,
  },
  title: {
    color: "#fff",
    fontWeight: "700",
    fontSize: 15,
  },
  meta: {
    color: "#94a3b8",
    fontSize: 11,
  },
});
