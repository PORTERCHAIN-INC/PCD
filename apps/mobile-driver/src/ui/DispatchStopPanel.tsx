import { useCallback, useEffect, useState } from "react";
import {
  ActionSheetIOS,
  Alert,
  Image,
  Linking,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import * as Location from "expo-location";
import { colors, radius, spacing } from "@porterchain/mobile-theme";
import { dispatchCheckin, fetchDispatchChecklist, fetchDispatchRoute } from "../api";
import {
  FAIL_REASONS,
  KIND_LABEL,
  isPickup,
  itemCount,
  primaryAction,
  type CheckinEvent,
  type DispatchRoute,
  type StopChecklist,
} from "../dispatchRoute";
import { capturePodPhotoDataUrl } from "../pod";
import { PrimaryButton } from "./PrimaryButton";

async function position() {
  try {
    const p = await Location.getLastKnownPositionAsync({ maxAge: 60_000 });
    return p
      ? {
          lat: p.coords.latitude,
          lng: p.coords.longitude,
          accuracy_m: p.coords.accuracy ?? undefined,
        }
      : {};
  } catch {
    return {};
  }
}

/** Multi-stop route: one primary button per stop (Arrived → Picked up / Delivered), checklist, POD. */
export function DispatchStopPanel() {
  const [route, setRoute] = useState<DispatchRoute | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [checklist, setChecklist] = useState<StopChecklist | null>(null);
  const [ticked, setTicked] = useState<Set<string>>(new Set());
  const [photo, setPhoto] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setRoute((await fetchDispatchRoute()).route);
    } catch {
      setRoute(null);
    } finally {
      setLoaded(true);
    }
  }, []);
  useEffect(() => void load(), [load]);

  const stop = route && route.next_index != null ? route.stops[route.next_index] : null;
  const stopId = stop?.keys.join(",") ?? "";
  useEffect(() => {
    setTicked(new Set());
    setPhoto(null);
    setError(null);
    setChecklist(null);
    if (stop && isPickup(stop.kind) && stop.status === "arrived") {
      fetchDispatchChecklist(stop.order_id)
        .then(setChecklist)
        .catch(() => setChecklist({ items: [], item_count: 0, box_count: 0 }));
    }
  }, [stopId, stop?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!loaded || !route || route.total === 0) return null; // legacy single-job flow below still works

  const send = async (event: CheckinEvent, note?: string) => {
    if (!stop) return;
    setBusy(true);
    setError(null);
    try {
      const out = await dispatchCheckin({
        keys: stop.keys,
        event,
        ...(await position()),
        ...(note ? { note } : {}),
        ...(event === "delivered" && photo ? { pod_photo: photo } : {}),
      });
      setRoute(out.route);
    } catch (e) {
      const m = e instanceof Error ? e.message : "failed";
      setError(
        m.startsWith("pod_required") ? "Take a delivery photo first." : m.replaceAll("_", " ")
      );
    } finally {
      setBusy(false);
    }
  };

  const fail = () => {
    const pick = (i: number) => {
      const r = FAIL_REASONS[i];
      if (r)
        Alert.alert("Can't complete", `Mark this stop failed: ${r}?`, [
          { text: "Back", style: "cancel" },
          { text: "Mark failed", style: "destructive", onPress: () => void send("failed", r) },
        ]);
    };
    if (Platform.OS === "ios") {
      ActionSheetIOS.showActionSheetWithOptions(
        { options: [...FAIL_REASONS, "Cancel"], cancelButtonIndex: FAIL_REASONS.length },
        pick
      );
    } else {
      Alert.alert(
        "Can't complete",
        undefined,
        FAIL_REASONS.slice(0, 3).map((r, i) => ({ text: r, onPress: () => pick(i) }))
      );
    }
  };

  if (!stop) {
    return (
      <View style={[styles.card, styles.doneCard]}>
        <Text style={styles.doneTitle}>Route complete</Text>
        <Text style={styles.doneSub}>{route.total} stops</Text>
      </View>
    );
  }
  const action = primaryAction(stop);
  const atStop = stop.status === "arrived";
  const items = checklist?.items ?? [];
  const needList = isPickup(stop.kind) && atStop;
  const ready =
    !busy &&
    (!needList || (checklist != null && ticked.size >= items.length)) &&
    (!(atStop && stop.needs_pod) || photo != null);
  const n = itemCount(checklist);
  const label =
    action?.event === "picked_up" && n
      ? `Picked up · ${n} item${n === 1 ? "" : "s"}`
      : (action?.label ?? "");

  return (
    <View style={styles.card} testID="dispatch-stop">
      <Text style={styles.count}>
        {route.done}
        <Text style={styles.countMuted}>/{route.total}</Text>
      </Text>
      <Text style={styles.kicker}>
        Stop {(route.next_index ?? 0) + 1} · {KIND_LABEL[stop.kind]}
      </Text>
      <Text style={styles.address}>{stop.address ?? "Address on file"}</Text>
      <Text style={styles.meta}>
        {stop.order_number ?? "—"} · {stop.boxes} box{stop.boxes === 1 ? "" : "es"}
      </Text>
      {stop.notes ? <Text style={styles.note}>{stop.notes}</Text> : null}

      {needList
        ? items.map((it) => {
            const id = it.item_key ?? it.boxes[0]?.package_id ?? it.label;
            const on = ticked.has(id);
            return (
              <Pressable
                key={id}
                accessibilityRole="checkbox"
                accessibilityState={{ checked: on }}
                onPress={() =>
                  setTicked((s) => {
                    const x = new Set(s);
                    if (x.has(id)) x.delete(id);
                    else x.add(id);
                    return x;
                  })
                }
                style={[styles.item, on && styles.itemOn]}
              >
                <Text style={[styles.itemLabel, on && styles.itemLabelOn]}>
                  {on ? "✓  " : ""}
                  {it.label}
                </Text>
                <Text style={[styles.itemRule, on && styles.itemLabelOn]}>
                  {it.rule ?? "1 box"}
                </Text>
              </Pressable>
            );
          })
        : null}

      {atStop && stop.needs_pod ? (
        <Pressable
          accessibilityRole="button"
          style={styles.photo}
          onPress={() =>
            capturePodPhotoDataUrl()
              .then(setPhoto)
              .catch((e: Error) => setError(e.message.replaceAll("_", " ")))
          }
        >
          {photo ? <Image source={{ uri: photo }} style={styles.thumb} /> : null}
          <Text style={styles.photoText}>
            {photo ? "Photo ready · retake" : "Take delivery photo"}
          </Text>
        </Pressable>
      ) : null}

      {error ? (
        <Text style={styles.error} accessibilityRole="alert">
          {error}
        </Text>
      ) : null}

      {action ? (
        <PrimaryButton
          label={busy ? "Saving…" : label}
          disabled={!ready}
          onPress={() => void send(action.event)}
          testID="dispatch-primary"
        />
      ) : null}
      <View style={styles.row}>
        {stop.lat != null && stop.lng != null && stop.status === "pending" ? (
          <Pressable
            accessibilityRole="link"
            style={styles.ghost}
            onPress={() =>
              void Linking.openURL(
                `https://www.google.com/maps/dir/?api=1&destination=${stop.lat},${stop.lng}`
              )
            }
          >
            <Text style={styles.ghostText}>Navigate</Text>
          </Pressable>
        ) : null}
        <Pressable accessibilityRole="button" style={styles.ghost} onPress={fail}>
          <Text style={styles.ghostText}>Can&apos;t complete</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.white,
    borderRadius: radius.lg,
    padding: spacing.xl,
    gap: spacing.md,
    marginBottom: spacing.lg,
  },
  doneCard: { backgroundColor: colors.primary, alignItems: "center" },
  doneTitle: { color: colors.white, fontSize: 28, fontWeight: "900" },
  doneSub: { color: "#cbd5e1", fontSize: 16 },
  count: { fontSize: 48, fontWeight: "900", color: colors.primary },
  countMuted: { color: colors.muted },
  kicker: {
    fontSize: 13,
    fontWeight: "800",
    letterSpacing: 1.5,
    textTransform: "uppercase",
    color: "#075985",
  },
  address: { fontSize: 24, fontWeight: "900", color: colors.primary },
  meta: { fontSize: 15, color: "#475569" },
  note: {
    backgroundColor: "#fffbeb",
    color: "#78350f",
    padding: spacing.md,
    borderRadius: radius.md,
  },
  item: {
    minHeight: 56,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: "#e2e8f0",
    paddingHorizontal: spacing.lg,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  itemOn: { backgroundColor: colors.primary, borderColor: colors.primary },
  itemLabel: { fontSize: 16, fontWeight: "700", color: colors.primary },
  itemLabelOn: { color: colors.white },
  itemRule: { fontSize: 14, color: "#475569" },
  photo: {
    minHeight: 64,
    borderRadius: radius.md,
    borderWidth: 2,
    borderStyle: "dashed",
    borderColor: "#cbd5e1",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.md,
  },
  thumb: { width: 48, height: 48, borderRadius: 8 },
  photoText: { fontSize: 16, fontWeight: "700", color: colors.primary },
  error: { color: colors.danger, fontWeight: "600" },
  row: { flexDirection: "row", gap: spacing.md },
  ghost: {
    flex: 1,
    minHeight: 52,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: "#cbd5e1",
    alignItems: "center",
    justifyContent: "center",
  },
  ghostText: { fontSize: 16, fontWeight: "700", color: colors.primary },
});
