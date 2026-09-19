import { useCallback, useEffect, useState } from "react";
import { Text, View, StyleSheet } from "react-native";
import { colors, radius, spacing, typography } from "@porterchain/mobile-theme";
import { fetchAssignedRoute, fetchRouteEarnings, fetchRouteStops, startRoute } from "../api";
import { formatCents } from "../format";
import { PrimaryButton } from "./PrimaryButton";
import type { AssignedRoute, RouteStopRow } from "../types";

type Props = {
  routeId: string | null;
  busy: boolean;
  onStarted: () => void;
  onError: (message: string) => void;
};

export function RouteControls({ routeId, busy, onStarted, onError }: Props) {
  const [assigned, setAssigned] = useState<AssignedRoute | null>(null);
  const [stops, setStops] = useState<RouteStopRow[]>([]);
  const [earningsCents, setEarningsCents] = useState<number | null>(null);
  const [action, setAction] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const route = await fetchAssignedRoute();
      setAssigned(route);
      const id = route?.id ?? routeId;
      if (!id) {
        setStops([]);
        setEarningsCents(null);
        return;
      }
      const [stopPayload, earn] = await Promise.all([
        fetchRouteStops(id).catch(() => ({ stops: [] as RouteStopRow[] })),
        fetchRouteEarnings(id).catch(() => ({ earnings_cents: 0 })),
      ]);
      setStops(stopPayload.stops ?? []);
      setEarningsCents(earn.earnings_cents ?? route?.earnings_cents ?? null);
    } catch (err) {
      onError(err instanceof Error ? err.message : "route_failed");
    }
  }, [onError, routeId]);

  useEffect(() => {
    void load();
  }, [load]);

  const id = assigned?.id ?? routeId;
  if (!id && !assigned) return null;

  const locked = busy || Boolean(action);

  return (
    <View style={styles.wrap} testID="route-controls">
      <Text style={styles.title}>Route</Text>
      <Text style={styles.meta}>
        {id ? `Route ${id.slice(0, 10)}…` : "No assigned route"}
        {assigned?.status ? ` · ${assigned.status.replace(/_/g, " ")}` : ""}
      </Text>
      <Text style={styles.meta}>
        Stops {assigned?.completed_stops ?? "—"}/
        {assigned?.stop_count ?? (stops.length > 0 ? stops.length : "—")}
        {earningsCents != null ? ` · ${formatCents(earningsCents)}` : ""}
      </Text>
      {id ? (
        <PrimaryButton
          tone="ghost"
          label={action === "start" ? "Starting…" : "Start route"}
          disabled={locked}
          onPress={() => {
            setAction("start");
            void startRoute(id)
              .then(() => {
                setNote("Route started");
                onStarted();
                return load();
              })
              .catch((err: unknown) => {
                onError(err instanceof Error ? err.message : "start_route_failed");
              })
              .finally(() => setAction(null));
          }}
        />
      ) : null}
      {stops.slice(0, 4).map((stop) => (
        <Text key={stop.stop_id} style={styles.stop}>
          {(stop.stop_type || "stop").replace(/_/g, " ")} ·{" "}
          {(stop.status || "pending").replace(/_/g, " ")} ·{" "}
          {stop.formatted_address || stop.order_id || stop.stop_id}
        </Text>
      ))}
      {note ? <Text style={styles.note}>{note}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: spacing.sm,
    backgroundColor: colors.white,
    borderRadius: radius.xl,
    padding: spacing.md,
  },
  title: { ...typography.title, fontSize: 18, color: colors.primary },
  meta: { ...typography.caption, color: colors.muted },
  stop: { ...typography.caption, color: colors.primary },
  note: { ...typography.caption, color: colors.secondary, fontWeight: "600" },
});
