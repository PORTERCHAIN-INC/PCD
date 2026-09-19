import { Text, View, StyleSheet, ScrollView } from "react-native";
import { colors, radius, spacing, typography } from "@porterchain/mobile-theme";
import { formatCents, formatEtaMinutes } from "../format";
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
  onDismissOfflineNote: () => void;
  onPodChange: (next: PodDraft) => void;
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
  onDismissOfflineNote,
  onPodChange,
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
            {handshake.routePolyline ? "Route geometry ready (Fleetbase / Valhalla)" : "Navigation"}
            {handshake.navStopCount != null ? ` · ${handshake.navStopCount} stops on route` : ""}
          </Text>
        ) : null}
        <Text style={styles.status} testID="route-status">
          {handshake.api === "up"
            ? "Live API · Maps for turn-by-turn · GPS → Fleetbase (incl. background)"
            : "API down — actions queue offline when possible"}
        </Text>
        {offlinePending > 0 ? (
          <Text style={styles.warn} testID="offline-pending">
            {offlinePending} offline action{offlinePending === 1 ? "" : "s"} waiting to sync
          </Text>
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
