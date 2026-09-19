import { Text, View, StyleSheet, ScrollView } from "react-native";
import { colors, radius, spacing, typography } from "@porterchain/mobile-theme";
import { formatCents, formatEtaMinutes } from "../format";
import type { FlushResult } from "../offline";
import { buildStopChecklist } from "../stopChecklist";
import { PrimaryButton } from "../ui/PrimaryButton";
import { Kpi } from "../ui/Card";
import { Screen } from "../ui/Screen";
import { StatusRail } from "../ui/StatusRail";
import { PodCapture, type PodDraft } from "../ui/PodCapture";
import { FieldOpsPanel } from "../ui/FieldOpsPanel";
import { RouteControls } from "../ui/RouteControls";
import type { Handshake } from "../types";

type Props = {
  handshake: Handshake;
  refreshing: boolean;
  action: string | null;
  navBusy: boolean;
  podDraft: PodDraft;
  offlinePending: number;
  offlineNote: string | null;
  lastFlush: FlushResult | null;
  scanComplete: boolean;
  onDismissOfflineNote: () => void;
  onPodChange: (next: PodDraft) => void;
  onScanCompleteChange: (complete: boolean) => void;
  onRefresh: () => void;
  onDuty: () => void;
  onArrive: () => void;
  onComplete: () => void;
  onAccept: () => void;
  onNavigate: () => void;
  onException: (reason: string) => void;
  onFlushOffline: () => void;
  onPhotoError: (message: string) => void;
};

export function RouteScreen({
  handshake,
  refreshing,
  action,
  navBusy,
  podDraft,
  offlinePending,
  offlineNote,
  lastFlush,
  scanComplete,
  onDismissOfflineNote,
  onPodChange,
  onScanCompleteChange,
  onRefresh,
  onDuty,
  onArrive,
  onComplete,
  onAccept,
  onNavigate,
  onException,
  onFlushOffline,
  onPhotoError,
}: Props) {
  const name = handshake.driverName ?? "Driver";
  const duty = handshake.online ? "On duty" : "Off duty";
  const next = handshake.nextStop?.trim() || "No assigned stop";
  const stops =
    handshake.stopsDone != null && handshake.stopsTotal != null
      ? `${handshake.stopsDone} / ${handshake.stopsTotal} stops today`
      : "Stops load after handshake";
  const busy = refreshing || Boolean(action);
  const canArrive = Boolean(handshake.routeId && handshake.stopId);
  const arrived = (handshake.stopStatus ?? "").toLowerCase().includes("arriv");
  const canAccept = Boolean(handshake.currentOrderId) && !canArrive;
  const canNav = Boolean(
    handshake.nextStop || handshake.navigationUrl || handshake.destLat != null
  );
  const needsPod = canArrive && (handshake.nextStopType ?? "").toLowerCase() !== "pickup";
  const otpRequired = handshake.otpRequired;
  const canComplete =
    canArrive &&
    (!needsPod || Boolean(podDraft.photoUrl)) &&
    (!otpRequired || Boolean(podDraft.otp.trim()));
  const needsScan =
    canArrive &&
    ((handshake.scanPickup?.required ?? 0) > 0 || (handshake.scanDelivery?.required ?? 0) > 0);
  const checklist = buildStopChecklist({
    hasStop: canArrive,
    arrived,
    needsScan,
    scanComplete: scanComplete || !needsScan,
    needsPod,
    podReady: Boolean(podDraft.photoUrl) && (!otpRequired || Boolean(podDraft.otp.trim())),
    completed: false,
  });
  const syncedHint =
    lastFlush && lastFlush.synced && (lastFlush.queued > 0 || lastFlush.gps_flushed > 0)
      ? `Last sync OK · ${lastFlush.queued + lastFlush.gps_flushed} flushed`
      : lastFlush && lastFlush.failed > 0
        ? `${lastFlush.failed} failed last sync`
        : null;

  return (
    <Screen testID="mobile-track">
      <StatusRail handshake={handshake} />
      <ScrollView
        style={styles.flex}
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.identity}>
          <Text style={styles.hello}>Hello, {name}</Text>
          <Text style={[styles.duty, handshake.online ? styles.on : styles.off]}>{duty}</Text>
        </View>
        <View style={styles.kpis}>
          <Kpi label="Wallet" value={formatCents(handshake.walletCents)} />
          <Kpi label="Today" value={formatCents(handshake.todayEarningsCents)} />
        </View>
        <Text style={styles.kicker}>
          {handshake.nextStopType ? `${handshake.nextStopType} stop` : "Next stop"}
        </Text>
        <Text style={styles.next}>{next}</Text>
        {handshake.currentOrderNumber ? (
          <Text style={styles.stops}>Job {handshake.currentOrderNumber}</Text>
        ) : null}
        <Text style={styles.stops}>{stops}</Text>
        <Text style={styles.meta}>
          ETA {handshake.etaLabel ?? formatEtaMinutes(handshake.etaMinutes)}
          {handshake.distanceLabel ? ` · ${handshake.distanceLabel}` : ""}
        </Text>
        {handshake.routePolyline || handshake.navStopCount != null ? (
          <Text style={styles.meta} testID="nav-geometry">
            {handshake.routePolyline ? "Route geometry ready (Valhalla / OSRM)" : "Navigation"}
            {handshake.navStopCount != null ? ` · ${handshake.navStopCount} stops on route` : ""}
          </Text>
        ) : null}
        <Text style={styles.status} testID="route-status">
          {handshake.api === "up"
            ? "Live API · Navigate uses Valhalla URL · GPS → Fleetbase"
            : "API down — actions queue offline when possible"}
        </Text>
        {offlinePending > 0 || syncedHint ? (
          <View style={styles.offlineBanner} testID="offline-banner">
            {offlinePending > 0 ? (
              <Text style={styles.warn} testID="offline-pending">
                {offlinePending} offline action{offlinePending === 1 ? "" : "s"} waiting to sync
              </Text>
            ) : (
              <Text style={styles.synced} testID="offline-synced">
                Offline queue clear
              </Text>
            )}
            {syncedHint ? <Text style={styles.meta}>{syncedHint}</Text> : null}
          </View>
        ) : null}
        {offlineNote ? (
          <View style={styles.conflict} testID="offline-conflict">
            <Text style={styles.warn}>{offlineNote}</Text>
            <PrimaryButton tone="ghost" label="Dismiss" onPress={onDismissOfflineNote} />
          </View>
        ) : null}
        {handshake.error ? <Text style={styles.error}>{handshake.error}</Text> : null}
        <Text style={styles.push}>{handshake.push.detail}</Text>
        <Text style={styles.push}>{handshake.location.detail}</Text>

        {checklist.length > 0 ? (
          <View style={styles.checklist} testID="stop-checklist">
            <Text style={styles.kicker}>This stop</Text>
            {checklist
              .filter((step) => step.status !== "skip")
              .map((step, index) => (
                <Text
                  key={step.id}
                  style={[
                    styles.checkRow,
                    step.status === "done" && styles.checkDone,
                    step.status === "current" && styles.checkCurrent,
                  ]}
                  testID={`checklist-${step.id}`}
                >
                  {index + 1}. {step.label}
                  {step.status === "done" ? " ✓" : step.status === "current" ? " ←" : ""}
                </Text>
              ))}
          </View>
        ) : null}

        <RouteControls
          routeId={handshake.routeId}
          busy={busy}
          onStarted={onRefresh}
          onError={onPhotoError}
        />

        {needsPod && arrived ? (
          <PodCapture
            busy={busy}
            draft={podDraft}
            orderId={handshake.currentOrderId}
            otpRequired={otpRequired}
            onChange={onPodChange}
            onPhotoError={onPhotoError}
          />
        ) : null}

        {canArrive ? (
          <FieldOpsPanel
            orderId={handshake.currentOrderId}
            stopType={handshake.nextStopType}
            busy={busy}
            seed={{
              otpRequired: handshake.otpRequired,
              scanPickup: handshake.scanPickup,
              scanDelivery: handshake.scanDelivery,
              codAmountCents: handshake.codAmountCents,
              codStatus: handshake.codStatus,
              currentOrderNumber: handshake.currentOrderNumber,
            }}
            onError={onPhotoError}
            onScanProgress={(complete) => onScanCompleteChange(complete)}
          />
        ) : null}

        {canArrive && arrived ? <ExceptionRow busy={busy} onException={onException} /> : null}
      </ScrollView>
      <View style={styles.cta}>
        <PrimaryButton
          label={
            action === "duty" ? "Updating duty…" : handshake.online ? "Go off duty" : "Go on duty"
          }
          disabled={busy || handshake.auth !== "up"}
          onPress={onDuty}
        />
        {canAccept ? (
          <PrimaryButton
            label={action === "accept" ? "Accepting…" : "Accept job"}
            disabled={busy}
            onPress={onAccept}
          />
        ) : null}
        {canNav ? (
          <PrimaryButton
            tone="ghost"
            label={navBusy ? "Opening maps…" : "Navigate"}
            disabled={busy || navBusy}
            onPress={onNavigate}
          />
        ) : null}
        {canArrive && !arrived ? (
          <PrimaryButton
            label={action === "arrive" ? "Marking arrived…" : "I've arrived"}
            disabled={busy}
            onPress={onArrive}
          />
        ) : null}
        {canArrive ? (
          <PrimaryButton
            testID="complete-stop"
            label={
              action === "deliver"
                ? "Completing…"
                : needsPod
                  ? "Complete with POD"
                  : "Complete stop"
            }
            disabled={busy || !canComplete}
            onPress={onComplete}
          />
        ) : null}
        {offlinePending > 0 ? (
          <PrimaryButton
            tone="ghost"
            testID="sync-offline"
            label={action === "flush" ? "Syncing…" : "Sync offline queue"}
            disabled={busy}
            onPress={onFlushOffline}
          />
        ) : null}
        <PrimaryButton
          testID="track-refresh"
          tone="ghost"
          label={refreshing ? "Refreshing…" : "Refresh"}
          disabled={busy}
          onPress={onRefresh}
        />
      </View>
    </Screen>
  );
}

function ExceptionRow({
  busy,
  onException,
}: {
  busy: boolean;
  onException: (reason: string) => void;
}) {
  return (
    <View style={styles.exception}>
      <Text style={styles.kicker}>Cannot complete?</Text>
      <PrimaryButton
        tone="danger"
        label="Report exception"
        disabled={busy}
        onPress={() => onException("unable_to_deliver")}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  scroll: {
    gap: spacing.md,
    paddingBottom: spacing.md,
  },
  flex: { flex: 1 },
  identity: {
    gap: spacing.xs,
  },
  hello: {
    ...typography.title,
    color: colors.primary,
  },
  duty: {
    ...typography.caption,
    fontWeight: "700",
  },
  on: { color: colors.driverGreen },
  off: { color: colors.muted },
  kpis: {
    flexDirection: "row",
    gap: spacing.md,
    backgroundColor: colors.white,
    borderRadius: radius.xl,
    padding: spacing.md,
  },
  kicker: {
    ...typography.caption,
    color: colors.muted,
    textTransform: "uppercase",
    letterSpacing: 1.1,
  },
  next: {
    ...typography.title,
    fontSize: 28,
    lineHeight: 34,
    color: colors.primary,
  },
  stops: {
    ...typography.body,
    color: colors.primary,
  },
  meta: {
    ...typography.caption,
    color: colors.secondary,
    fontWeight: "600",
  },
  status: {
    ...typography.caption,
    color: colors.muted,
  },
  warn: {
    ...typography.caption,
    color: colors.danger,
    fontWeight: "600",
  },
  synced: {
    ...typography.caption,
    color: colors.driverGreen,
    fontWeight: "600",
  },
  offlineBanner: {
    gap: spacing.xs,
    backgroundColor: colors.white,
    borderRadius: radius.xl,
    padding: spacing.md,
  },
  checklist: {
    gap: spacing.xs,
    backgroundColor: colors.white,
    borderRadius: radius.xl,
    padding: spacing.md,
  },
  checkRow: {
    ...typography.body,
    color: colors.muted,
  },
  checkDone: {
    color: colors.driverGreen,
  },
  checkCurrent: {
    color: colors.primary,
    fontWeight: "700",
  },
  conflict: {
    gap: spacing.sm,
    backgroundColor: colors.white,
    borderRadius: radius.xl,
    padding: spacing.md,
  },
  error: {
    ...typography.caption,
    color: colors.danger,
  },
  push: {
    ...typography.caption,
    color: colors.muted,
  },
  exception: {
    gap: spacing.sm,
  },
  cta: {
    backgroundColor: colors.white,
    borderRadius: radius.xl,
    padding: spacing.md,
    gap: spacing.sm,
  },
});
