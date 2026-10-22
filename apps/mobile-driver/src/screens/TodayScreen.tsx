/**
 * Today: one glance, one action. Off duty → vehicle check → Go on duty.
 * On duty → shift glance (done / left / earned) → next stop with live ETA → Open stop.
 */
import { useEffect, useState } from "react";
import { Linking, Pressable, StyleSheet, Text, View } from "react-native";
import { gpsDisabledMessage } from "../location";
import { useEarnings } from "../data/queries";
import { UpdatedAgo } from "../ui/UpdatedAgo";

const onDutyFlag = (h: { online?: boolean | null }) => Boolean(h.online);
import { haptic } from "../haptics";
import type { FieldSession } from "../hooks/useFieldSession";
import type { RouteState } from "../hooks/useDispatchRoute";
import { KIND_LABEL } from "../dispatchRoute";
import { openTurnByTurn } from "../maps";
import { emptyPretrip, PRETRIP_ITEMS, pretripComplete, type PretripChecks } from "../pretrip";
import { clockLabel, distanceLabel, etaCountdown, money, moneyShort } from "../smart/geo";
import { isClosed, needsAccept, normState, openStopAvailable } from "../stop/stopFlow";
import type { DriverJobSummary } from "../types";
import { Banner, Button, Label, Screen } from "../ui/kit";
import { LiveDot, PressScale, Rise, Skeleton } from "../ui/motion";
import { ScanLookupButton } from "../ui/ScanLookup";
import { SosButton, useSos } from "../ui/SosButton";
import { SyncBanners } from "../ui/SyncBanners";
import { SyncPill } from "../ui/SyncPill";
import { color, maxFontScale, radius, space, target, type } from "../ui/theme";
import { useNow } from "../ui/useNow";

type Props = {
  field: FieldSession;
  route: RouteState;
  action: string | null;
  onOpenJob: () => void;
  onGoOnDuty: (pretrip: PretripChecks) => void;
  onGoOffDuty: () => void;
  onSync: () => void;
};

const STATE_COPY: Record<string, string> = {
  DRIVER_ASSIGNED: "New — accept or decline",
  DRIVER_ACCEPTED: "Accepted · go to pickup",
  DRIVER_EN_ROUTE: "Going to pickup",
  AT_PICKUP: "At pickup",
  PICKED_UP: "Picked up · go to drop-off",
  IN_TRANSIT: "Going to drop-off",
  AT_DESTINATION: "At drop-off",
  DELIVERED: "Delivered",
  COMPLETED: "Done",
};

function jobStatus(job: DriverJobSummary): string {
  const s = normState(job.state ?? job.status);
  return STATE_COPY[s] ?? s.replace(/_/g, " ").toLowerCase();
}

export function TodayScreen({
  field,
  route: r,
  action,
  onOpenJob,
  onGoOnDuty,
  onGoOffDuty,
  onSync,
}: Props) {
  const { handshake: h, busy, pending, rejected, refresh, setError } = field;
  const [pretrip, setPretrip] = useState<PretripChecks>(emptyPretrip());
  const earnings = useEarnings(onDutyFlag(h));
  const earned = earnings.data?.today_cents ?? null;
  const sos = useSos();
  const onDuty = Boolean(h.online);
  const open = h.jobs.filter((j) => !isClosed(j.state ?? j.status));
  const route = r.route && r.route.total > 0 ? r.route : null;
  const done = route ? route.done : (h.stopsDone ?? 0);
  const total = route ? route.total : (h.stopsTotal ?? 0);
  // "Open stop" only when there is a stop to open (or a new offer to review). A job with
  // no actionable stop used to show the button and land on an empty Job tab.
  const hasWork = openStopAvailable({
    currentOrderId: h.currentOrderId,
    stopId: h.stopId,
    orderState: h.currentOrderState,
    hasRouteStop: Boolean(r.stop),
  });
  const stuckJob = onDuty && !hasWork && Boolean(h.currentOrderId);
  const ready = pretripComplete(pretrip);
  const firstLoad = h.api === "idle" && busy;
  const now = useNow(onDuty && Boolean(r.etaAt));

  // A finished stop changes earnings: refresh in the background (cached value stays on screen).
  useEffect(() => {
    if (onDuty && done) void earnings.refetch();
  }, [onDuty, done]); // eslint-disable-line react-hooks/exhaustive-deps

  const checked = PRETRIP_ITEMS.filter((i) => pretrip[i.id]).length;
  const footer = !onDuty ? (
    <Button
      tone="primary"
      testID="go-on-duty"
      label={ready ? "Go on duty" : `Vehicle check ${checked}/${PRETRIP_ITEMS.length}`}
      hint="Starts your shift and shares your location with dispatch"
      busy={action === "duty"}
      disabled={!ready || h.auth !== "up"}
      onPress={() => onGoOnDuty(pretrip)}
    />
  ) : hasWork ? (
    <Button
      tone="primary"
      testID="open-job"
      label={needsAccept(h.currentOrderState) ? "New job — review" : "Open stop"}
      onPress={onOpenJob}
    />
  ) : null;

  const first = h.driverName?.split(" ")[0];
  const next = r.stop;

  return (
    <Screen
      testID="mobile-track"
      footer={footer}
      onRefresh={() => void refresh()}
      refreshing={busy}
    >
      <View style={styles.head}>
        <View
          style={styles.status}
          accessibilityLabel={onDuty ? "You are on duty" : "You are off duty"}
        >
          <LiveDot on={onDuty} />
          <Text style={[styles.statusText, onDuty && styles.statusOn]}>
            {onDuty ? "ON DUTY" : "OFF DUTY"}
          </Text>
        </View>
        <View style={styles.headRight}>
          <SyncPill
            offline={h.api === "down"}
            pending={pending}
            rejected={rejected}
            onSync={onSync}
          />
          <SosButton onAsk={sos.ask} />
        </View>
      </View>
      {onDuty ? <ScanLookupButton currentOrderId={h.currentOrderId} onOpenJob={onOpenJob} /> : null}

      <UpdatedAgo
        at={Math.max(field.updatedAt, r.updatedAt ?? 0)}
        fetching={busy || r.fetching}
        offline={h.api === "down"}
      />
      <Text style={styles.hello} maxFontSizeMultiplier={maxFontScale} accessibilityRole="header">
        {firstLoad
          ? "Today"
          : onDuty
            ? next
              ? "Next stop"
              : hasWork
                ? "On the job"
                : "Waiting for work"
            : first
              ? `Ready, ${first}?`
              : "Ready?"}
      </Text>

      {sos.page}
      {sos.state === "sent" ? (
        <Banner tone="success" title="SOS sent. Dispatch will call you." />
      ) : null}
      {sos.state === "failed" ? (
        <Banner
          tone="danger"
          title="SOS did not send"
          body="No connection. Call dispatch or 911."
        />
      ) : null}

      {stuckJob ? (
        <Banner
          tone="warn"
          title="This job has no next stop yet"
          body={`${h.currentOrderNumber ?? "Your job"} is on your list but has nothing to do right now. Pull down to refresh. If it stays like this, contact dispatch from Help.`}
        />
      ) : null}

      <SyncBanners
        offline={false}
        pending={0}
        rejected={rejected}
        error={h.error}
        onSync={onSync}
        onDismissError={() => setError(null)}
      />

      {firstLoad ? (
        <View style={styles.skel} testID="today-skeleton">
          <Skeleton height={96} />
          <Skeleton height={180} />
          <Skeleton height={64} />
        </View>
      ) : !onDuty ? (
        <Rise>
          <View style={styles.card} testID="pretrip-check">
            <Label>Vehicle check · 30 seconds</Label>
            <View style={styles.grid}>
              {PRETRIP_ITEMS.map((item) => {
                const on = pretrip[item.id];
                return (
                  <PressScale
                    key={item.id}
                    accessibilityRole="checkbox"
                    accessibilityState={{ checked: on }}
                    accessibilityLabel={item.label}
                    onPress={() => {
                      haptic.tap();
                      setPretrip({ ...pretrip, [item.id]: !on });
                    }}
                    style={[styles.check, on && styles.checkOn]}
                    testID={`pretrip-${item.id}`}
                  >
                    <Text style={[styles.checkMark, on && styles.checkMarkOn]}>
                      {on ? "✓" : "○"}
                    </Text>
                    <Text style={[styles.checkText, on && styles.checkTextOn]} numberOfLines={2}>
                      {item.label}
                    </Text>
                  </PressScale>
                );
              })}
            </View>
          </View>
        </Rise>
      ) : (
        <>
          <Rise index={0}>
            <View style={styles.glance} testID="today-progress">
              <Stat label="Done" value={`${done}`} />
              <Stat label="Left" value={`${Math.max(0, total - done)}`} />
              <Stat label="Earned" value={moneyShort(earned)} accent />
            </View>
            <View
              style={styles.bar}
              accessibilityRole="progressbar"
              accessibilityValue={{ min: 0, max: total || 1, now: done }}
            >
              <View
                style={[
                  styles.barFill,
                  { width: `${total ? Math.min(100, (done / total) * 100) : 0}%` },
                ]}
              />
            </View>
          </Rise>

          {next ? (
            <Rise index={1}>
              <PressScale
                accessibilityRole="button"
                accessibilityLabel={`Next stop: ${next.address ?? "address on file"}. Open stop.`}
                onPress={onOpenJob}
                style={styles.hero}
                testID="today-next-stop"
              >
                <Label style={styles.kicker}>
                  {KIND_LABEL[next.kind]} · stop {(r.route?.next_index ?? 0) + 1}
                </Label>
                <Text style={styles.heroAddr} numberOfLines={2} maxFontSizeMultiplier={1.4}>
                  {next.address ?? "Address on file"}
                </Text>
                {r.etaAt && next.status === "pending" ? (
                  <View style={styles.etaRow}>
                    <Text style={styles.eta}>{etaCountdown(r.etaAt, now)}</Text>
                    <Text style={styles.etaMeta}>
                      {r.distance != null ? `${distanceLabel(r.distance)} · ` : ""}arrive{" "}
                      {clockLabel(r.etaAt)}
                    </Text>
                  </View>
                ) : (
                  <Text style={styles.etaMeta}>
                    {next.status === "arrived" ? "You're at this stop" : "Locating…"}
                  </Text>
                )}
              </PressScale>
              {next.status === "pending" ? (
                <View style={styles.navWrap}>
                  <Button
                    label="Navigate"
                    testID="today-navigate"
                    onPress={() =>
                      void openTurnByTurn({
                        lat: next.lat,
                        lng: next.lng,
                        address: next.address,
                      }).catch((e: Error) => setError(e.message))
                    }
                  />
                </View>
              ) : null}
            </Rise>
          ) : h.nextStop ? (
            <Rise index={1}>
              <PressScale
                onPress={onOpenJob}
                style={styles.hero}
                accessibilityRole="button"
                testID="today-next-stop"
              >
                <Label style={styles.kicker}>{h.nextStopType ?? "Next"}</Label>
                <Text style={styles.heroAddr} numberOfLines={2}>
                  {h.nextStop}
                </Text>
                {h.etaLabel ? <Text style={styles.etaMeta}>{h.etaLabel}</Text> : null}
              </PressScale>
            </Rise>
          ) : null}

          {h.location.kind === "denied" || h.location.kind === "error" ? (
            <Banner
              tone="warn"
              title={h.location.kind === "denied" ? "Location is off" : "Location problem"}
              body={h.location.detail}
              action={{ label: "Open Settings", onPress: () => void Linking.openSettings() }}
            />
          ) : h.location.kind === "searching" ? (
            <Banner tone="info" title="Waiting for GPS" body={h.location.detail} />
          ) : h.online && h.location.kind === "idle" && gpsDisabledMessage() ? (
            <Banner
              tone="warn"
              title="Location sharing is paused"
              body={gpsDisabledMessage() ?? ""}
            />
          ) : null}

          {open.length === 0 && !route ? (
            <View style={styles.empty} testID="today-empty">
              <LiveDot on size={14} />
              <Text style={styles.emptyTitle}>You're live</Text>
              <Text style={styles.emptyBody}>Stay on duty — new jobs ring this phone.</Text>
            </View>
          ) : null}

          {open.length > 0 ? <Label>Jobs today</Label> : null}
          {open.map((job, i) => {
            const current = job.order_id === h.currentOrderId;
            return (
              <Rise key={job.order_id} index={i + 2}>
                <Pressable
                  accessibilityRole={current ? "button" : "text"}
                  accessibilityLabel={`Job ${job.order_number}. ${jobStatus(job)}. To ${job.delivery_address ?? "drop-off"}`}
                  disabled={!current}
                  onPress={onOpenJob}
                  style={[styles.job, current && styles.jobCurrent]}
                  testID={`job-${job.order_id}`}
                >
                  <View style={styles.jobHead}>
                    <Text style={styles.jobNo}>#{job.order_number}</Text>
                    <Text style={[styles.jobState, current && styles.jobStateNow]}>
                      {current ? "NOW" : jobStatus(job)}
                    </Text>
                  </View>
                  {job.delivery_address ? (
                    <Text style={styles.jobAddr} numberOfLines={1}>
                      {job.delivery_address}
                    </Text>
                  ) : null}
                </Pressable>
              </Rise>
            );
          })}

          <Button
            tone="quiet"
            label="Go off duty"
            testID="go-off-duty"
            busy={action === "duty"}
            onPress={onGoOffDuty}
          />
        </>
      )}
    </Screen>
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <View style={styles.stat} accessibilityLabel={`${label}: ${value}`}>
      <Text style={[styles.statValue, accent && styles.statAccent]} maxFontSizeMultiplier={1.3}>
        {value}
      </Text>
      <Text style={styles.statLabel}>{label.toUpperCase()}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  head: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  headRight: { flexDirection: "row", alignItems: "center", gap: space.sm },
  status: { flexDirection: "row", alignItems: "center", gap: 2 },
  statusText: { ...type.label, color: color.inkFaint },
  statusOn: { color: color.primary },
  hello: { ...type.display, color: color.ink, marginTop: space.sm },
  skel: { gap: space.md },
  card: {
    backgroundColor: color.surface,
    borderRadius: radius.xl,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: color.border,
    padding: space.lg,
    gap: space.md,
  },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: space.sm },
  check: {
    width: "48.5%",
    minHeight: target.primary,
    borderRadius: radius.lg,
    backgroundColor: color.surface2,
    padding: space.md,
    gap: space.xs,
    justifyContent: "center",
  },
  checkOn: { backgroundColor: color.accentSoft },
  checkMark: { fontSize: 22, color: color.inkFaint, fontWeight: "900" },
  checkMarkOn: { color: color.primary },
  checkText: { ...type.small, color: color.inkMuted, fontWeight: "700" },
  checkTextOn: { color: color.ink },
  glance: { flexDirection: "row", gap: space.sm },
  stat: {
    flex: 1,
    backgroundColor: color.surface,
    borderRadius: radius.lg,
    paddingVertical: space.lg,
    paddingHorizontal: space.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: color.border,
  },
  statValue: { ...type.title, color: color.ink, fontVariant: ["tabular-nums"] },
  statAccent: { color: color.primary },
  statLabel: { ...type.label, color: color.inkFaint, marginTop: 2 },
  bar: {
    height: 6,
    borderRadius: 3,
    backgroundColor: color.surface2,
    overflow: "hidden",
    marginTop: space.md,
  },
  barFill: { height: 6, backgroundColor: color.primary },
  hero: {
    backgroundColor: color.surface,
    borderRadius: radius.xl,
    borderWidth: 1,
    borderColor: color.primary,
    padding: space.xl,
    gap: space.sm,
  },
  kicker: { color: color.primary },
  heroAddr: { ...type.title, color: color.ink },
  etaRow: { flexDirection: "row", alignItems: "baseline", gap: space.md },
  eta: { ...type.hero, color: color.primary, fontVariant: ["tabular-nums"] },
  etaMeta: { ...type.small, color: color.inkMuted },
  navWrap: { marginTop: space.sm },
  empty: { alignItems: "center", paddingVertical: space.xxl, gap: space.sm },
  emptyTitle: { ...type.title, color: color.ink },
  emptyBody: { ...type.body, color: color.inkMuted, textAlign: "center" },
  job: {
    backgroundColor: color.surface,
    borderRadius: radius.lg,
    padding: space.lg,
    gap: space.xs,
    borderWidth: 1,
    borderColor: color.border,
  },
  jobCurrent: { borderColor: color.primary },
  jobHead: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: space.sm,
  },
  jobNo: { ...type.bodyStrong, color: color.ink },
  jobState: { ...type.small, color: color.inkMuted, flexShrink: 1, textAlign: "right" },
  jobStateNow: { ...type.label, color: color.primary },
  jobAddr: { ...type.body, color: color.inkMuted },
});
