/**
 * The current stop. One big primary action at a time, decided by stop/stopFlow:
 * Accept → Arrived → Scan → Proof → Complete. Everything else is secondary.
 */
import { useState } from "react";
import { Alert, Linking, StyleSheet, TextInput, View } from "react-native";
import {
  acceptOrder,
  arriveStop,
  codCheckout,
  rejectOrder,
  reportException,
  scanPackage,
} from "../api";
import { formatCents } from "../format";
import type { FieldSession } from "../hooks/useFieldSession";
import { openTurnByTurn } from "../maps";
import { runOnlineOrQueue } from "../offline";
import { capturePodPhotoDataUrl } from "../pod";
import { completeStop } from "../stop/completeStop";
import { emptyPodDraft, type PodDraft } from "../stop/podDraft";
import { deriveStop, type PrimaryAction } from "../stop/stopFlow";
import { BarcodeScannerModal } from "../ui/BarcodeScannerModal";
import { ProblemSheet } from "../ui/job/ProblemSheet";
import { ProofSheets, type ProofSheet } from "../ui/job/ProofSheets";
import { StepRail } from "../ui/job/StepRail";
import {
  Banner,
  Body,
  Button,
  Card,
  EmptyState,
  Label,
  Muted,
  Screen,
  Strong,
  Title,
} from "../ui/kit";
import { Sheet } from "../ui/Sheet";
import { SyncBanners } from "../ui/SyncBanners";
import { color, radius, space, target, type } from "../ui/theme";

type Props = {
  field: FieldSession;
  action: string | null;
  pod: PodDraft;
  setPod: (next: PodDraft) => void;
  run: (name: string, work: () => Promise<unknown>) => Promise<void>;
  onGoToday: () => void;
  onSync: () => void;
};

export function JobScreen({ field, action, pod, setPod, run, onGoToday, onSync }: Props) {
  const {
    handshake: h,
    pending,
    rejected,
    syncingStopIds,
    refresh,
    setError,
    setHandshake,
  } = field;
  const [scanOpen, setScanOpen] = useState(false);
  const [typeCode, setTypeCode] = useState<string | null>(null);
  const [sheet, setSheet] = useState<ProofSheet>(null);
  const [problemOpen, setProblemOpen] = useState(false);

  const scanPhase = (h.nextStopType ?? "").toLowerCase() === "pickup" ? "pickup" : "delivery";
  const scan = scanPhase === "pickup" ? h.scanPickup : h.scanDelivery;
  const view = deriveStop({
    orderState: h.currentOrderState,
    stopType: h.nextStopType,
    stopStatus: h.stopStatus,
    hasStop: Boolean(h.routeId && h.stopId),
    onDuty: Boolean(h.online),
    syncing: Boolean(h.stopId && syncingStopIds.includes(h.stopId)),
    scanRequired: scan?.required ?? 0,
    scanComplete: Boolean(scan?.complete),
    pod,
    podRequirements: h.podRequirements,
    otpRequired: h.otpRequired,
  });
  const routeId = h.routeId ?? "";
  const stopId = h.stopId ?? "";
  const orderId = h.currentOrderId ?? "";
  const busy = Boolean(action);
  const arrivedOrLater = ["scan", "proof", "complete"].includes(view.step);
  const codDue =
    (h.codAmountCents ?? 0) > 0 && !["collected", "payout_processed"].includes(h.codStatus ?? "");

  const submitScan = (code: string) =>
    run("scan", async () => {
      const res = await scanPackage(orderId, code.trim(), scanPhase);
      const progress = {
        scanned: res.scanned,
        required: res.required,
        complete: res.complete,
        missing_suffixes: res.missing_suffixes ?? [],
      };
      setHandshake((prev) =>
        scanPhase === "pickup"
          ? { ...prev, scanPickup: progress }
          : { ...prev, scanDelivery: progress }
      );
    });

  const doPrimary = (a: PrimaryAction) => {
    switch (a) {
      case "accept":
        return void run("accept", () => acceptOrder(orderId));
      case "go_on_duty":
        return onGoToday();
      case "arrive":
        return void run("arrive", () =>
          runOnlineOrQueue("arrive_stop", { stop_id: stopId, route_id: routeId }, () =>
            arriveStop(routeId, stopId)
          )
        );
      case "scan":
        return setScanOpen(true);
      case "photo":
        return void capturePodPhotoDataUrl()
          .then((photoUrl) => setPod({ ...pod, photoUrl }))
          .catch((e: unknown) => setError(e instanceof Error ? e.message : "photo_failed"));
      case "signature":
      case "id_check":
      case "otp":
        return setSheet(a);
      case "complete":
        return void run("complete", async () => {
          await completeStop({
            routeId,
            stopId,
            kind: view.kind,
            otpRequired: h.otpRequired,
            podRequirements: h.podRequirements,
            pod,
          });
          setPod(emptyPodDraft());
        });
    }
  };

  if (view.step === "none" || view.step === "waiting") {
    return (
      <Screen testID="screen-job" onRefresh={() => void refresh()} refreshing={field.busy}>
        <SyncBanners
          offline={h.api === "down"}
          pending={pending}
          rejected={rejected}
          error={h.error}
          onSync={onSync}
          onDismissError={() => setError(null)}
        />
        <EmptyState
          testID="job-empty"
          title={view.step === "waiting" ? "Waiting on dispatch" : "No active job"}
          body={
            view.step === "waiting"
              ? "Dispatch is updating this job. Pull down to refresh."
              : "When dispatch sends you a job it shows up here."
          }
        />
      </Screen>
    );
  }

  const kindLabel = view.kind === "pickup" ? "Pickup" : "Drop-off";
  const policy = h.podRequirements ?? { enforced: true, photo_or_signature: true };
  const strictPhotoOrSig = Boolean(policy.photo || policy.signature);
  const proofRows = [
    ...(policy.photo_or_signature && !strictPhotoOrSig
      ? [
          {
            label: "Photo or signature",
            done: Boolean(pod.photoUrl || pod.signature),
            redo: () => doPrimary("photo"),
          },
        ]
      : []),
    ...(policy.photo
      ? [{ label: "Photo", done: Boolean(pod.photoUrl), redo: () => doPrimary("photo") }]
      : []),
    ...(policy.signature
      ? [{ label: "Signature", done: Boolean(pod.signature), redo: () => setSheet("signature") }]
      : []),
    ...(policy.id_check
      ? [{ label: "ID checked", done: pod.idNameMatches, redo: () => setSheet("id_check") }]
      : []),
    ...(h.otpRequired || policy.otp
      ? [{ label: "Receiver code", done: Boolean(pod.otp), redo: () => setSheet("otp") }]
      : []),
  ];
  const hasNav =
    view.step === "arrive" && Boolean(h.navigationUrl || h.destLat != null || h.nextStop);
  const footer = (
    <>
      {view.primary ? (
        <Button
          tone="primary"
          testID={view.primary.action === "scan" ? "scan-camera" : `primary-${view.primary.action}`}
          label={view.primary.label}
          busy={
            action === view.primary.action ||
            (view.primary.action === "complete" && action === "complete")
          }
          disabled={busy && action !== view.primary.action}
          onPress={() => view.primary && doPrimary(view.primary.action)}
        />
      ) : null}
      {view.step === "offer" ? (
        <Button
          label="Decline"
          busy={action === "decline"}
          disabled={busy}
          onPress={() =>
            Alert.alert("Decline this job?", "Dispatch will offer it to another driver.", [
              { text: "Keep it", style: "cancel" },
              {
                text: "Decline",
                style: "destructive",
                onPress: () => void run("decline", () => rejectOrder(orderId)),
              },
            ])
          }
        />
      ) : null}
      {hasNav ? (
        <Button
          label="Navigate"
          hint="Opens your maps app"
          onPress={() =>
            void openTurnByTurn({
              navigationUrl: h.navigationUrl,
              lat: h.destLat,
              lng: h.destLng,
              address: h.nextStop,
            }).catch((e: unknown) => setError(e instanceof Error ? e.message : "navigate_failed"))
          }
        />
      ) : null}
    </>
  );

  return (
    <Screen
      testID="screen-job"
      footer={view.primary || view.step === "offer" || hasNav ? footer : undefined}
      onRefresh={() => void refresh()}
      refreshing={field.busy}
    >
      <SyncBanners
        offline={h.api === "down"}
        pending={view.step === "syncing" ? 0 : pending}
        rejected={rejected}
        error={h.error}
        onSync={onSync}
        onDismissError={() => setError(null)}
      />
      {view.step === "syncing" ? (
        <Banner
          tone="success"
          testID="stop-syncing"
          title="Delivered, syncing"
          body="Saved on this phone. It sends by itself when you have signal."
        />
      ) : null}
      {view.step === "off_duty" ? (
        <Banner
          tone="warn"
          title="You're off duty"
          body="Go on duty from Today to work this stop."
        />
      ) : null}

      <View style={styles.head}>
        <Label style={view.kind === "pickup" ? styles.kindPickup : styles.kindDrop}>
          {view.step === "offer" ? "New job" : kindLabel}
          {h.currentOrderNumber ? ` · #${h.currentOrderNumber}` : ""}
        </Label>
        <Title testID="stop-address" accessibilityRole="header">
          {h.nextStop ?? "Address loading…"}
        </Title>
        {h.etaLabel || h.distanceLabel ? (
          <Muted>{[h.etaLabel, h.distanceLabel].filter(Boolean).join(" · ")}</Muted>
        ) : null}
      </View>
      <StepRail steps={view.rail} />

      {h.accessNotes ? (
        <Card testID="access-notes">
          <Label>Access</Label>
          <Body>{h.accessNotes}</Body>
        </Card>
      ) : null}
      {h.parcelLines.length || (h.deliveryAttempts ?? 0) > 0 ? (
        <Card>
          <Label>Parcels</Label>
          {h.parcelLines.map((line, i) => (
            <Body key={`${i}-${line}`}>{line}</Body>
          ))}
          {(h.deliveryAttempts ?? 0) > 0 ? (
            <Strong>
              Attempt {h.deliveryAttempts} of {h.maxDeliveryAttempts ?? 2}
            </Strong>
          ) : null}
        </Card>
      ) : null}

      {view.step === "scan" ? (
        <Card testID="scan-card">
          <Label>Scan</Label>
          <Title>
            {scan?.scanned ?? 0} of {scan?.required ?? 0} scanned
          </Title>
          {(scan?.missing_suffixes?.length ?? 0) > 0 ? (
            <Muted>Still to scan: {scan?.missing_suffixes?.join(", ")}</Muted>
          ) : null}
          <Button
            tone="quiet"
            label="Label won't scan? Type the code"
            onPress={() => setTypeCode("")}
          />
        </Card>
      ) : null}

      {view.kind === "delivery" && arrivedOrLater ? (
        <Card testID="proof-card">
          <Label>Proof of delivery</Label>
          {proofRows.map((row) => (
            <ProofRow key={row.label} label={row.label} done={row.done} onRedo={row.redo} />
          ))}
        </Card>
      ) : null}

      {codDue && arrivedOrLater ? (
        <Banner
          tone="warn"
          testID="cod-due"
          title={`Collect ${formatCents(h.codAmountCents)} payment`}
          action={{
            label: "Open payment link",
            onPress: () =>
              void run("cod", async () => {
                const res = await codCheckout(orderId);
                if (res.checkout_url) await Linking.openURL(res.checkout_url);
              }),
          }}
        />
      ) : null}

      {arrivedOrLater ? (
        <Button
          tone="quiet"
          label="Can't complete this stop"
          testID="open-problem"
          onPress={() => setProblemOpen(true)}
        />
      ) : null}

      <BarcodeScannerModal
        visible={scanOpen}
        onClose={() => setScanOpen(false)}
        onScan={(code) => void submitScan(code)}
      />
      <ProofSheets
        open={sheet}
        pod={pod}
        pharmacy={Boolean(h.podRequirements?.reasons?.includes("pharmacy_medical"))}
        onChange={setPod}
        onClose={() => setSheet(null)}
      />
      <ProblemSheet
        visible={problemOpen}
        busy={action === "problem"}
        onClose={() => setProblemOpen(false)}
        onError={setError}
        onReport={(reason, photoUrl) =>
          void run("problem", async () => {
            await reportException(routeId, stopId, reason, undefined, photoUrl);
            setProblemOpen(false);
            setPod(emptyPodDraft());
          })
        }
      />
      <Sheet
        visible={typeCode !== null}
        title="Type the label code"
        onClose={() => setTypeCode(null)}
        footer={
          <Button
            tone="primary"
            label="Add"
            disabled={!typeCode?.trim()}
            onPress={() => {
              const code = typeCode ?? "";
              setTypeCode(null);
              void submitScan(code);
            }}
          />
        }
      >
        <TextInput
          style={styles.input}
          value={typeCode ?? ""}
          onChangeText={setTypeCode}
          autoCapitalize="characters"
          autoFocus
          accessibilityLabel="Label code"
          placeholder="Code under the barcode"
          placeholderTextColor={color.inkMuted}
        />
      </Sheet>
    </Screen>
  );
}

function ProofRow({ label, done, onRedo }: { label: string; done: boolean; onRedo: () => void }) {
  return (
    <View style={styles.proofRow} accessibilityLabel={`${label}: ${done ? "done" : "not yet"}`}>
      <Body>
        {done ? "✓ " : "○ "}
        {label}
      </Body>
      {done ? <Button tone="quiet" label="Redo" onPress={onRedo} /> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  head: { gap: space.xs },
  kindPickup: { color: color.infoInk },
  kindDrop: { color: color.primary },
  proofRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    minHeight: 48,
  },
  input: {
    ...type.heading,
    minHeight: target.min,
    borderRadius: radius.md,
    borderWidth: 2,
    borderColor: color.ink,
    backgroundColor: color.surface,
    paddingHorizontal: space.md,
    color: color.ink,
  },
});
