/**
 * The next stop on a dispatch route, as one hero card with one primary action.
 * Arrived → (checklist / proof only if the server needs it) → Picked up / Delivered.
 */
import { useEffect, useState } from "react";
import {
  ActionSheetIOS,
  Alert,
  Image,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { fetchDispatchChecklist } from "../api";
import {
  FAIL_REASONS,
  KIND_LABEL,
  isPickup,
  itemCount,
  primaryAction,
  type StopChecklist,
} from "../dispatchRoute";
import { humanError } from "../errorCopy";
import { haptic } from "../haptics";
import type { RouteState } from "../hooks/useDispatchRoute";
import { openTurnByTurn } from "../maps";
import { capturePodPhotoDataUrl } from "../pod";
import { clockLabel, distanceLabel, etaCountdown } from "../smart/geo";
import { Banner, Button, Label } from "./kit";
import { PressScale, Rise } from "./motion";
import { color, maxFontScale, radius, space, target, type } from "./theme";
import { useNow } from "./useNow";

export function RouteStopCard({ r }: { r: RouteState }) {
  const { route, stop } = r;
  const [busy, setBusy] = useState(false);
  const [checklist, setChecklist] = useState<StopChecklist | null>(null);
  const [ticked, setTicked] = useState<Set<string>>(new Set());
  const [photo, setPhoto] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const now = useNow(Boolean(r.etaAt) && stop?.status === "pending");

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

  if (!route || route.total === 0) return null;

  if (!stop) {
    return (
      <Rise>
        <View style={[styles.card, styles.doneCard]} testID="route-complete">
          <Text style={styles.doneMark}>✓</Text>
          <Text style={styles.doneTitle} maxFontSizeMultiplier={maxFontScale}>
            Route complete
          </Text>
          <Text style={styles.doneSub}>{route.total} stops · nice work</Text>
        </View>
      </Rise>
    );
  }

  const action = primaryAction(stop);
  const atStop = stop.status === "arrived";
  const items = checklist?.items ?? [];
  const needList = isPickup(stop.kind) && atStop;
  const needPhoto = atStop && stop.needs_pod;
  const ready =
    !busy &&
    (!needList || (checklist != null && ticked.size >= items.length)) &&
    (!needPhoto || photo != null);
  const n = itemCount(checklist);
  const label =
    action?.event === "picked_up" && n
      ? `Picked up · ${n} item${n === 1 ? "" : "s"}`
      : !ready && needPhoto && !photo
        ? "Take the proof photo first"
        : (action?.label ?? "");

  const send = async (event: NonNullable<typeof action>["event"], note?: string) => {
    setBusy(true);
    setError(null);
    try {
      await r.checkin(event, {
        ...(note ? { note } : {}),
        ...(event === "delivered" && photo ? { pod_photo: photo } : {}),
      });
    } catch (e) {
      haptic.error();
      const m = e instanceof Error ? e.message : "failed";
      setError(m.startsWith("pod_required") ? "Take a delivery photo first." : humanError(m));
    } finally {
      setBusy(false);
    }
  };

  const fail = () => {
    const pick = (i: number) => {
      const reason = FAIL_REASONS[i];
      if (reason)
        Alert.alert("Can't complete", `Mark this stop failed: ${reason}?`, [
          { text: "Back", style: "cancel" },
          { text: "Mark failed", style: "destructive", onPress: () => void send("failed", reason) },
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
        FAIL_REASONS.slice(0, 3).map((reason, i) => ({ text: reason, onPress: () => pick(i) }))
      );
    }
  };

  const eta = r.etaAt && stop.status === "pending" ? etaCountdown(r.etaAt, now) : null;
  // One main action: while driving it's Navigate; at the stop it's the check-in.
  const driving = stop.status === "pending" && (r.distance == null || r.distance > 300);
  const navigate = () =>
    void openTurnByTurn({ lat: stop.lat, lng: stop.lng, address: stop.address }).catch((e: Error) =>
      setError(e.message)
    );

  return (
    <Rise>
      <View style={styles.card} testID="dispatch-stop">
        <View style={styles.topRow}>
          <Label style={styles.kicker}>
            Stop {(route.next_index ?? 0) + 1} of {route.total} · {KIND_LABEL[stop.kind]}
          </Label>
          <Text style={styles.count}>
            {route.done}
            <Text style={styles.countMuted}>/{route.total}</Text>
          </Text>
        </View>
        <Text style={styles.address} maxFontSizeMultiplier={1.4} testID="stop-address">
          {stop.address ?? "Address on file"}
        </Text>

        {eta ? (
          <View style={styles.etaRow} accessibilityLabel={`Arriving in ${eta}`} testID="stop-eta">
            <Text style={styles.eta}>{eta}</Text>
            <Text style={styles.etaMeta}>
              {r.distance != null ? `${distanceLabel(r.distance)} · ` : ""}
              {r.etaAt ? `arrive ${clockLabel(r.etaAt)}` : ""}
            </Text>
          </View>
        ) : null}

        <View style={styles.chips}>
          <Chip text={`#${stop.order_number ?? "—"}`} />
          <Chip text={`${stop.boxes} box${stop.boxes === 1 ? "" : "es"}`} />
          {stop.liftgate ? <Chip text="Liftgate" tone="warn" testID="stop-liftgate" /> : null}
          {stop.needs_pod ? <Chip text="Photo proof" /> : null}
        </View>
        {stop.notes ? <Text style={styles.note}>“{stop.notes}”</Text> : null}

        {r.autoArrived && atStop ? (
          <Banner
            tone="success"
            title="You're here — marked arrived"
            body="We saw you reach the stop."
          />
        ) : null}
        {r.queued ? (
          <Banner
            tone="info"
            title="Saved on this phone"
            body="It syncs by itself when you're back online."
          />
        ) : null}

        {needList
          ? items.map((it) => {
              const id = it.item_key ?? it.boxes[0]?.package_id ?? it.label;
              const on = ticked.has(id);
              return (
                <Pressable
                  key={id}
                  accessibilityRole="checkbox"
                  accessibilityState={{ checked: on }}
                  onPress={() => {
                    haptic.tap();
                    setTicked((s) => {
                      const x = new Set(s);
                      if (x.has(id)) x.delete(id);
                      else x.add(id);
                      return x;
                    });
                  }}
                  style={[styles.item, on && styles.itemOn]}
                >
                  <Text style={[styles.itemLabel, on && styles.itemLabelOn]}>
                    {on ? "✓  " : ""}
                    {it.label}
                  </Text>
                  <Text style={styles.itemRule}>{it.rule ?? "1 box"}</Text>
                </Pressable>
              );
            })
          : null}

        {needPhoto ? (
          <PressScale
            accessibilityRole="button"
            accessibilityLabel={photo ? "Retake proof photo" : "Take proof photo"}
            style={[styles.photo, photo && styles.photoDone]}
            onPress={() =>
              capturePodPhotoDataUrl()
                .then((p) => {
                  haptic.success();
                  setPhoto(p);
                })
                .catch((e: Error) => setError(humanError(e.message)))
            }
            testID="stop-photo"
          >
            {photo ? <Image source={{ uri: photo }} style={styles.thumb} /> : null}
            <Text style={styles.photoText}>
              {photo ? "Photo ready · retake" : "📷  Take proof photo"}
            </Text>
          </PressScale>
        ) : null}

        {error ? (
          <Text style={styles.error} accessibilityRole="alert">
            {error}
          </Text>
        ) : null}

        {driving ? (
          <>
            <Button
              tone="primary"
              label="Navigate"
              testID="stop-navigate"
              hint="Opens turn-by-turn directions in your maps app"
              onPress={navigate}
            />
            <View style={styles.row}>
              <View style={styles.flex}>
                <Button
                  label="I'm here"
                  busy={busy}
                  testID="dispatch-primary"
                  hint="Marks you arrived. Happens by itself when you pull up."
                  onPress={() => void send("arrived")}
                />
              </View>
              <View style={styles.flex}>
                <Button tone="quiet" label="Problem" onPress={fail} testID="stop-fail" />
              </View>
            </View>
          </>
        ) : (
          <>
            {action ? (
              <Button
                tone="primary"
                label={label}
                busy={busy}
                disabled={!ready}
                onPress={() => void send(action.event)}
                testID="dispatch-primary"
              />
            ) : null}
            <Button tone="quiet" label="Problem with this stop" onPress={fail} testID="stop-fail" />
          </>
        )}
      </View>
    </Rise>
  );
}

function Chip({ text, tone, testID }: { text: string; tone?: "warn"; testID?: string }) {
  return (
    <View style={[styles.chip, tone === "warn" && styles.chipWarn]} testID={testID}>
      <Text style={[styles.chipText, tone === "warn" && styles.chipTextWarn]}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: color.surface,
    borderRadius: radius.xl,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: color.border,
    padding: space.xl,
    gap: space.md,
  },
  doneCard: { alignItems: "center", backgroundColor: color.accentSoft, borderColor: color.primary },
  doneMark: { fontSize: 56, color: color.primary, fontWeight: "900" },
  doneTitle: { ...type.display, color: color.ink },
  doneSub: { ...type.body, color: color.inkMuted },
  topRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  kicker: { color: color.primary },
  count: { ...type.mono, color: color.ink },
  countMuted: { color: color.inkFaint },
  address: { ...type.display, color: color.ink },
  etaRow: { flexDirection: "row", alignItems: "baseline", gap: space.md },
  eta: { ...type.hero, color: color.primary, fontVariant: ["tabular-nums"] },
  etaMeta: { ...type.small, color: color.inkMuted },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: space.sm },
  chip: {
    backgroundColor: color.surface2,
    borderRadius: radius.pill,
    paddingHorizontal: space.md,
    paddingVertical: 6,
  },
  chipWarn: { backgroundColor: color.warnSoft },
  chipText: { ...type.small, color: color.inkMuted, fontWeight: "700" },
  chipTextWarn: { color: color.warnInk },
  note: { ...type.body, color: color.inkMuted, fontStyle: "italic" },
  item: {
    minHeight: target.min,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: color.border,
    paddingHorizontal: space.lg,
    justifyContent: "center",
  },
  itemOn: { backgroundColor: color.accentSoft, borderColor: color.primary },
  itemLabel: { ...type.bodyStrong, color: color.ink },
  itemLabelOn: { color: color.successInk },
  itemRule: { ...type.small, color: color.inkFaint },
  photo: {
    minHeight: target.primary,
    borderRadius: radius.lg,
    borderWidth: 2,
    borderStyle: "dashed",
    borderColor: color.border,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: space.md,
    padding: space.sm,
  },
  photoDone: { borderStyle: "solid", borderColor: color.primary },
  thumb: { width: 56, height: 56, borderRadius: radius.sm },
  photoText: { ...type.bodyStrong, color: color.ink },
  error: { ...type.bodyStrong, color: color.danger },
  row: { flexDirection: "row", gap: space.sm },
  flex: { flex: 1 },
});
