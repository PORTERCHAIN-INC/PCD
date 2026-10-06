import { Text, View, StyleSheet, ScrollView } from "react-native";
import { colors, radius, spacing, typography } from "@porterchain/mobile-theme";
import { formatCents, formatEtaMinutes, jobIsClosed, vehicleLabel } from "../format";
import { isDeliveryStop, jobNeedsAccept, stopWork } from "../jobActions";
import { fieldWarning } from "../fieldCopy";
import type { FlushResult } from "../offline";
import { buildStopChecklist } from "../stopChecklist";
import { PrimaryButton } from "../ui/PrimaryButton";
import { Kpi } from "../ui/Card";
import { Screen, DEV_MENU_GUTTER } from "../ui/Screen";
import { StatusRail } from "../ui/StatusRail";
import { PodCapture, type PodDraft } from "../ui/PodCapture";
import { FieldOpsPanel } from "../ui/FieldOpsPanel";
import { RouteControls } from "../ui/RouteControls";
import { ENFORCE_DROP_POD } from "../hooks/completeStopAction";
import { capturePodPhotoDataUrl } from "../pod";
import { STOP_EXCEPTION_TYPES, stopExceptionById } from "../stopExceptions";
import { emptyPretrip, PRETRIP_ITEMS, pretripComplete, type PretripChecks } from "../pretrip";
import type { Handshake } from "../types";
import { useState } from "react";

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
  onDuty: (pretrip?: Record<string, boolean>) => void;
  onArrive: () => void;
  onComplete: () => void;
  onAccept: () => void;
  onDecline: () => void;
  onNavigate: () => void;
  onException: (reason: string, notes?: string, photoUrl?: string) => void;
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
  onDecline,
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
  const [pretrip, setPretrip] = useState<PretripChecks>(emptyPretrip());
  const canStartDuty = handshake.online || pretripComplete(pretrip);
  const hasStop = Boolean(handshake.routeId && handshake.stopId);
  const arrived = (handshake.stopStatus ?? "").toLowerCase().includes("arriv");
  const offer = jobNeedsAccept({ state: handshake.currentOrderState ?? undefined });
  const work = stopWork(handshake.currentOrderState, handshake.nextStopType);
  const canAccept = Boolean(handshake.currentOrderId) && offer;
  const canWork = hasStop && (work.arrive || work.complete);
  const finished = jobIsClosed({ state: handshake.currentOrderState ?? undefined });
  const canNav = !finished && Boolean(handshake.navigationUrl || handshake.destLat != null);
  const needsPod = canWork && isDeliveryStop(handshake.nextStopType);
  const otpRequired = handshake.otpRequired;
  const canComplete =
    canWork &&
    work.complete &&
    (!ENFORCE_DROP_POD || !needsPod || Boolean(podDraft.photoUrl)) &&
    (!ENFORCE_DROP_POD || !otpRequired || Boolean(podDraft.otp.trim()));
  const needsScan =
    canWork &&
    ((handshake.scanPickup?.required ?? 0) > 0 || (handshake.scanDelivery?.required ?? 0) > 0);
  const checklist = buildStopChecklist({
    hasStop: canWork,
    arrived,
    needsScan,
    scanComplete: scanComplete || !needsScan,
    needsPod: ENFORCE_DROP_POD && needsPod,
    podReady: Boolean(podDraft.photoUrl) && (!otpRequired || Boolean(podDraft.otp.trim())),
    completed: false,
  });
  const syncedHint =
    lastFlush && lastFlush.synced && (lastFlush.queued > 0 || lastFlush.gps_flushed > 0)
      ? `Last sync OK · ${lastFlush.queued + lastFlush.gps_flushed} flushed`
      : lastFlush && lastFlush.failed > 0
        ? `${lastFlush.failed} failed last sync`
        : null;

  const pushWarn = fieldWarning(handshake.push.detail);
  const locationWarn = fieldWarning(handshake.location.detail);
  const handshakeWarn = fieldWarning(handshake.error);

  return (
    <Screen testID="mobile-track" includeBottomSafeArea={false}>
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
        {handshake.accessNotes ? (
          <Text style={styles.access} testID="next-stop-access">
            {handshake.accessNotes}
          </Text>
        ) : null}
        {handshake.bookingMode === "vehicle" ? (
          <Text style={styles.meta}>Whole vehicle · {vehicleLabel(handshake.vehicleClass)}</Text>
        ) : handshake.vehicleClass ? (
          <Text style={styles.meta}>Vehicle · {vehicleLabel(handshake.vehicleClass)}</Text>
        ) : null}
        {(handshake.parcelLines ?? []).map((line, index) => (
          <Text key={`${index}-${line}`} style={styles.meta}>
            {line}
          </Text>
        ))}
        {handshake.deliveryAttempts != null && handshake.deliveryAttempts > 0 ? (
          <Text style={styles.meta} testID="delivery-attempts">
            Attempt {handshake.deliveryAttempts} of {handshake.maxDeliveryAttempts ?? 2}
          </Text>
        ) : null}
        {handshake.currentOrderNumber ? (
          <Text style={styles.stops}>Job {handshake.currentOrderNumber}</Text>
        ) : null}
        <Text style={styles.stops}>{stops}</Text>
        {handshake.etaLabel || handshake.etaMinutes != null ? (
          <Text style={styles.meta}>
            ETA {handshake.etaLabel ?? formatEtaMinutes(handshake.etaMinutes)}
            {handshake.distanceLabel ? ` · ${handshake.distanceLabel}` : ""}
          </Text>
        ) : null}
        {handshake.routePolyline || handshake.navStopCount != null ? (
          <Text style={styles.meta} testID="nav-geometry">
            {handshake.routePolyline ? "Route geometry ready (Valhalla / OSRM)" : "Navigation"}
            {handshake.navStopCount != null ? ` · ${handshake.navStopCount} stops on route` : ""}
          </Text>
        ) : null}
        <Text style={styles.status} testID="route-status">
          {handshake.api === "up"
            ? "On the network · GPS to PorterChain dispatch"
            : "API down — queued work syncs when you reconnect"}
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
        {handshakeWarn ? <Text style={styles.error}>{handshakeWarn}</Text> : null}
        {pushWarn ? <Text style={styles.push}>{pushWarn}</Text> : null}
        {locationWarn ? <Text style={styles.push}>{locationWarn}</Text> : null}

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

        {canWork ? (
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

        {canWork && arrived ? <ExceptionRow busy={busy} onException={onException} /> : null}
        {!handshake.online ? <PretripRow checks={pretrip} onChange={setPretrip} /> : null}
      </ScrollView>
      <View style={styles.cta}>
        <PrimaryButton
          label={
            action === "duty" ? "Updating duty…" : handshake.online ? "Go off duty" : "Go on duty"
          }
          disabled={busy || handshake.auth !== "up" || !canStartDuty}
          onPress={() => onDuty(handshake.online ? undefined : pretrip)}
        />
        {canAccept ? (
          <PrimaryButton
            label={action === "accept" ? "Accepting…" : "Accept job"}
            disabled={busy}
            onPress={onAccept}
          />
        ) : null}
        {canAccept ? (
          <PrimaryButton
            tone="ghost"
            label={action === "decline" ? "Declining…" : "Decline"}
            disabled={busy}
            onPress={onDecline}
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
        {canWork && work.arrive && !arrived ? (
          <PrimaryButton
            label={action === "arrive" ? "Marking arrived…" : "I've arrived"}
            disabled={busy}
            onPress={onArrive}
          />
        ) : null}
        {canWork && work.complete ? (
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

function PretripRow({
  checks,
  onChange,
}: {
  checks: PretripChecks;
  onChange: (next: PretripChecks) => void;
}) {
  return (
    <View style={styles.exception} testID="pretrip-check">
      <Text style={styles.kicker}>30-second pre-trip</Text>
      <Text style={styles.meta}>Lights, tires, plates, leaks, winter kit — then go on duty.</Text>
      {PRETRIP_ITEMS.map((item) => (
        <PrimaryButton
          key={item.id}
          tone={checks[item.id] ? "primary" : "ghost"}
          label={`${checks[item.id] ? "✓ " : ""}${item.label}`}
          onPress={() => onChange({ ...checks, [item.id]: !checks[item.id] })}
        />
      ))}
    </View>
  );
}

function ExceptionRow({
  busy,
  onException,
}: {
  busy: boolean;
  onException: (reason: string, notes?: string, photoUrl?: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [code, setCode] = useState<string | null>(null);
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const [picking, setPicking] = useState(false);
  const selected = code ? stopExceptionById(code) : undefined;
  const needsPhoto = Boolean(selected?.photoRequired);
  const canSubmit = Boolean(code) && (!needsPhoto || Boolean(photoUrl));

  return (
    <View style={styles.exception} testID="stop-exception">
      <Text style={styles.kicker}>Cannot complete?</Text>
      {!open ? (
        <PrimaryButton
          tone="danger"
          label="Report exception"
          disabled={busy}
          onPress={() => setOpen(true)}
        />
      ) : (
        <>
          {STOP_EXCEPTION_TYPES.map((item) => (
            <PrimaryButton
              key={item.id}
              tone={code === item.id ? "danger" : "ghost"}
              label={item.label}
              disabled={busy}
              onPress={() => setCode(item.id)}
            />
          ))}
          {needsPhoto ? (
            <PrimaryButton
              tone="ghost"
              label={
                picking ? "Opening camera…" : photoUrl ? "Retake exception photo" : "Photo required"
              }
              disabled={busy || picking}
              onPress={() => {
                setPicking(true);
                void capturePodPhotoDataUrl()
                  .then((url) => setPhotoUrl(url))
                  .catch(() => setPhotoUrl(null))
                  .finally(() => setPicking(false));
              }}
            />
          ) : (
            <PrimaryButton
              tone="ghost"
              label={
                picking ? "Opening camera…" : photoUrl ? "Retake photo" : "Add photo (optional)"
              }
              disabled={busy || picking}
              onPress={() => {
                setPicking(true);
                void capturePodPhotoDataUrl()
                  .then((url) => setPhotoUrl(url))
                  .catch(() => setPhotoUrl(null))
                  .finally(() => setPicking(false));
              }}
            />
          )}
          <PrimaryButton
            tone="danger"
            testID="submit-exception"
            label={
              selected?.retryable
                ? "Log attempt — stay on stop"
                : selected
                  ? "Fail this stop"
                  : "Choose a reason"
            }
            disabled={busy || !canSubmit}
            onPress={() => {
              if (!code) return;
              onException(code, selected?.label, photoUrl ?? undefined);
            }}
          />
        </>
      )}
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
    paddingRight: DEV_MENU_GUTTER,
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
  access: {
    ...typography.body,
    color: colors.secondary,
    fontWeight: "600",
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
