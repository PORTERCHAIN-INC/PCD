/**
 * The next stop on a dispatch route, as one hero card with one primary action.
 * Arrived → (checklist / proof only if the server needs it) → Picked up / Delivered.
 */
import { useEffect, useState, type ReactNode } from "react";
import { Image, Linking, Platform, Pressable, StyleSheet, Text, View } from "react-native";
import { fetchDispatchChecklist, fetchStopContact } from "../api";
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
import { DriveMode } from "./DriveMode";
import { useLayout } from "./layout";
import { Sheet } from "./Sheet";
import { SwipeConfirm } from "./SwipeConfirm";
import { toast } from "./toast";
import { daySummary, headsUpText, loadOrder, stopWarnings } from "../smart/route";

/**
 * Returns the stop card (scrolls) and its actions (pinned in the Screen footer, in thumb reach),
 * plus the full-screen pages it can open (Problem, Drive mode, Load order).
 */
export function useRouteStopUi(
  r: RouteState,
  opts: { offline?: boolean } = {}
): { card: ReactNode; footer: ReactNode | undefined; pages: ReactNode } {
  const L = useLayout();
  const { route, stop } = r;
  const [busy, setBusy] = useState(false);
  const [checklist, setChecklist] = useState<StopChecklist | null>(null);
  const [ticked, setTicked] = useState<Set<string>>(new Set());
  const [photo, setPhoto] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const now = useNow(Boolean(r.etaAt) && stop?.status === "pending");
  const [page, setPage] = useState<null | "problem" | "drive" | "load">(null);
  const [reason, setReason] = useState<string | null>(null);

  const stopId = stop?.keys.join(",") ?? "";
  useEffect(() => {
    setTicked(new Set());
    setPhoto(null);
    setError(null);
    setChecklist(null);
    setReason(null);
    if (stop && isPickup(stop.kind) && stop.status === "arrived") {
      fetchDispatchChecklist(stop.order_id)
        .then(setChecklist)
        .catch(() => setChecklist({ items: [], item_count: 0, box_count: 0 }));
    }
  }, [stopId, stop?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!route || route.total === 0) return { card: null, footer: undefined, pages: null };

  if (!stop) {
    const d = daySummary(route);
    return {
      footer: undefined,
      pages: null,
      card: (
        <Rise>
          <View style={[styles.card, styles.doneCard]} testID="route-complete">
            <Text style={styles.doneMark}>✓</Text>
            <Text style={styles.doneTitle} maxFontSizeMultiplier={maxFontScale}>
              Route complete
            </Text>
            <Text style={styles.doneSub}>
              {d.done} of {d.total} stops · nice work
            </Text>
            <View style={styles.statGrid} testID="day-summary">
              <Stat n={d.drops} label="Delivered" />
              <Stat n={d.pickups} label="Picked up" />
              <Stat n={d.boxes} label="Boxes" />
              <Stat n={d.failed} label="Problems" warn={d.failed > 0} />
            </View>
            {d.proofs ? <Text style={styles.doneSub}>{d.proofs} photo proofs sent</Text> : null}
          </View>
        </Rise>
      ),
    };
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
    haptic.press();
    setReason(null);
    setPage("problem");
  };

  const contact = async (how: "call" | "text") => {
    haptic.tap();
    try {
      const { phone } = await fetchStopContact(
        stop.order_id,
        isPickup(stop.kind) ? "pickup" : "drop"
      );
      const etaMin = r.etaAt ? (r.etaAt - Date.now()) / 60_000 : null;
      const sep = Platform.OS === "ios" ? "&" : "?";
      await Linking.openURL(
        how === "call"
          ? `tel:${phone}`
          : `sms:${phone}${sep}body=${encodeURIComponent(headsUpText(etaMin, stop.kind))}`
      );
    } catch (e) {
      const m = e instanceof Error ? e.message : "";
      toast.show(
        "warn",
        m.includes("no_contact_phone") ? "No phone on file" : "Couldn't reach the customer",
        m.includes("no_contact_phone") ? "Ask dispatch to contact them." : humanError(m)
      );
    }
  };

  const eta = r.etaAt && stop.status === "pending" ? etaCountdown(r.etaAt, now) : null;
  // One main action: while driving it's Navigate; at the stop it's the check-in.
  const driving = stop.status === "pending" && (r.distance == null || r.distance > 300);
  const warnings = stopWarnings({
    stop,
    fixAgeMs: r.fixAt ? Date.now() - r.fixAt : null,
    accuracyM: r.fix?.accuracy ?? null,
    battery: null,
    offline: Boolean(opts.offline),
    speedMps: r.fix?.speed ?? null,
  });
  const loads = loadOrder(route);
  const navigate = () =>
    void openTurnByTurn({ lat: stop.lat, lng: stop.lng, address: stop.address }).catch((e: Error) =>
      toast.show("warn", "Couldn't open maps", e.message)
    );

  const card = (
    <Rise>
      <View style={[styles.card, L.compact && styles.cardCompact]} testID="dispatch-stop">
        <View style={styles.topRow}>
          <Label style={styles.kicker}>
            Stop {(route.next_index ?? 0) + 1} of {route.total} · {KIND_LABEL[stop.kind]}
          </Label>
          <Text style={styles.count}>
            {route.done}
            <Text style={styles.countMuted}>/{route.total}</Text>
          </Text>
        </View>
        {warnings.map((w) => (
          <Text
            key={w.id}
            style={[styles.warn, w.tone === "danger" && styles.warnDanger]}
            testID={`warn-${w.id}`}
          >
            ⚠ {w.text}
          </Text>
        ))}
        <Text
          style={[styles.address, L.compact && styles.addressCompact]}
          maxFontSizeMultiplier={1.4}
          testID="stop-address"
        >
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

        <View style={styles.tools}>
          <Tool label="Call" onPress={() => void contact("call")} testID="stop-call" />
          <Tool label="Text ETA" onPress={() => void contact("text")} testID="stop-text" />
          <Tool label="Drive mode" onPress={() => setPage("drive")} testID="stop-drive" />
          {loads.length > 1 ? (
            <Tool label="Load order" onPress={() => setPage("load")} testID="stop-load" />
          ) : null}
        </View>

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
      </View>
    </Rise>
  );

  const footer = (
    <>
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
          {action && action.event !== "arrived" ? (
            <SwipeConfirm
              label={label}
              busy={busy}
              disabled={!ready}
              onConfirm={() => void send(action.event)}
              testID="dispatch-primary"
            />
          ) : action ? (
            <Button
              tone="primary"
              label={label}
              busy={busy}
              onPress={() => void send(action.event)}
              testID="dispatch-primary"
            />
          ) : null}
          <Button tone="quiet" label="Problem with this stop" onPress={fail} testID="stop-fail" />
        </>
      )}
    </>
  );

  const etaMin = r.etaAt ? (r.etaAt - now) / 60_000 : null;
  const pages = (
    <>
      <Sheet
        visible={page === "problem"}
        title="What went wrong?"
        kicker={`Stop ${(route.next_index ?? 0) + 1} · ${KIND_LABEL[stop.kind]}`}
        tone="danger"
        onClose={() => setPage(null)}
        testID="page-problem"
        footer={
          <SwipeConfirm
            tone="danger"
            label={reason ? "Swipe to mark failed" : "Pick a reason"}
            disabled={!reason}
            busy={busy}
            onConfirm={() => {
              if (!reason) return;
              setPage(null);
              void send("failed", reason);
            }}
            testID="problem-confirm"
          />
        }
      >
        <Text style={styles.pageBody}>{stop.address ?? "This stop"}</Text>
        {FAIL_REASONS.map((x) => (
          <Pressable
            key={x}
            accessibilityRole="radio"
            accessibilityState={{ selected: reason === x }}
            onPress={() => {
              haptic.tap();
              setReason(x);
            }}
            style={[styles.item, reason === x && styles.itemDanger]}
            testID={`reason-${x}`}
          >
            <Text style={styles.itemLabel}>
              {reason === x ? "●  " : "○  "}
              {x}
            </Text>
          </Pressable>
        ))}
      </Sheet>
      <Sheet
        visible={page === "load"}
        title="Load order"
        kicker="Back of the van first"
        onClose={() => setPage(null)}
        testID="page-load"
      >
        <Text style={styles.pageBody}>
          Load from top to bottom: the last drop goes in first, the next drop sits by the door.
        </Text>
        {loads.map(({ stop: s, position }, i) => (
          <View key={s.keys.join(",")} style={styles.loadRow}>
            <Text style={styles.loadN}>{i + 1}</Text>
            <View style={styles.flex}>
              <Text style={styles.itemLabel} numberOfLines={1}>
                {s.address ?? "Address on file"}
              </Text>
              <Text style={styles.itemRule}>
                Stop {position} · {s.boxes} box{s.boxes === 1 ? "" : "es"}
                {i === loads.length - 1 ? " · by the door" : ""}
              </Text>
            </View>
          </View>
        ))}
      </Sheet>
      {page === "drive" ? (
        <DriveMode
          stop={stop}
          index={(route.next_index ?? 0) + 1}
          total={route.total}
          eta={eta}
          etaMin={etaMin}
          distance={r.distance}
          saver={r.saver}
          onNavigate={navigate}
          onArrived={() => void send("arrived")}
          onClose={() => setPage(null)}
        />
      ) : null}
    </>
  );

  return { card, footer, pages };
}

/** Back-compat wrapper (card + inline actions) for places without a Screen footer. */
export function RouteStopCard({ r }: { r: RouteState }) {
  const ui = useRouteStopUi(r);
  return (
    <>
      {ui.card}
      {ui.footer}
      {ui.pages}
    </>
  );
}

function Tool({ label, onPress, testID }: { label: string; onPress: () => void; testID?: string }) {
  return (
    <PressScale accessibilityRole="button" onPress={onPress} style={styles.tool} testID={testID}>
      <Text style={styles.toolText}>{label}</Text>
    </PressScale>
  );
}

function Stat({ n, label, warn }: { n: number; label: string; warn?: boolean }) {
  return (
    <View style={styles.stat}>
      <Text style={[styles.statN, warn && styles.statWarn]}>{n}</Text>
      <Text style={styles.statL}>{label}</Text>
    </View>
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
  cardCompact: { padding: space.lg, gap: space.sm + 2 },
  addressCompact: { fontSize: 24, lineHeight: 29 },
  warn: { ...type.small, fontWeight: "700", color: color.warnInk },
  warnDanger: { color: color.danger },
  tools: { flexDirection: "row", flexWrap: "wrap", gap: space.sm },
  tool: {
    minHeight: target.min,
    paddingHorizontal: space.md,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: color.border,
    justifyContent: "center",
  },
  toolText: { ...type.small, fontWeight: "800", color: color.ink },
  statGrid: { flexDirection: "row", gap: space.sm, marginTop: space.sm, alignSelf: "stretch" },
  stat: {
    flex: 1,
    alignItems: "center",
    paddingVertical: space.sm,
    borderRadius: radius.md,
    backgroundColor: color.surface,
  },
  statN: { ...type.display, color: color.ink, fontVariant: ["tabular-nums"] },
  statWarn: { color: color.warnInk },
  statL: { ...type.small, color: color.inkMuted },
  pageBody: { ...type.body, color: color.inkMuted },
  itemDanger: { borderColor: color.danger, backgroundColor: "#2A0F14" },
  loadRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.md,
    paddingVertical: space.sm,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: color.border,
  },
  loadN: {
    ...type.display,
    color: color.primary,
    width: 40,
    textAlign: "center",
    fontVariant: ["tabular-nums"],
  },
  row: { flexDirection: "row", gap: space.sm },
  flex: { flex: 1 },
});
