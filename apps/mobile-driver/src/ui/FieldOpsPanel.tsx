import { useEffect, useState } from "react";
import { Linking, Text, TextInput, View, StyleSheet } from "react-native";
import { colors, radius, spacing, typography } from "@porterchain/mobile-theme";
import { codCheckout, fetchJob, scanPackage } from "../api";
import { formatCents } from "../format";
import { BarcodeScannerModal } from "./BarcodeScannerModal";
import { PrimaryButton } from "./PrimaryButton";
import type { DriverJobDetail, Handshake, ScanProgress } from "../types";

type Props = {
  orderId: string | null;
  stopType: string | null;
  busy: boolean;
  /** Seed from handshake so scan/COD show before a second round-trip. */
  seed?: Pick<
    Handshake,
    | "otpRequired"
    | "scanPickup"
    | "scanDelivery"
    | "codAmountCents"
    | "codStatus"
    | "currentOrderNumber"
  > | null;
  onError: (message: string) => void;
  onScanProgress?: (complete: boolean) => void;
};

function seedJob(orderId: string, seed: NonNullable<Props["seed"]>): DriverJobDetail {
  return {
    order_id: orderId,
    order_number: seed.currentOrderNumber || orderId,
    tracking_number: "",
    otp_required: seed.otpRequired,
    scan_pickup: seed.scanPickup ?? undefined,
    scan_delivery: seed.scanDelivery ?? undefined,
    cod_amount_cents: seed.codAmountCents,
    cod_status: seed.codStatus,
  };
}

export function FieldOpsPanel({ orderId, stopType, busy, seed, onError, onScanProgress }: Props) {
  const [job, setJob] = useState<DriverJobDetail | null>(
    orderId && seed ? seedJob(orderId, seed) : null
  );
  const [code, setCode] = useState("");
  const [action, setAction] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [scanOpen, setScanOpen] = useState(false);

  useEffect(() => {
    if (!orderId) {
      setJob(null);
      return;
    }
    if (seed) setJob(seedJob(orderId, seed));
    let cancelled = false;
    void fetchJob(orderId)
      .then((next) => {
        if (!cancelled) setJob(next);
      })
      .catch((err: unknown) => {
        if (!cancelled && !seed) onError(err instanceof Error ? err.message : "job_detail_failed");
      });
    return () => {
      cancelled = true;
    };
  }, [orderId, seed?.otpRequired, seed?.codAmountCents, seed?.codStatus]);

  useEffect(() => {
    if (!job || !onScanProgress) return;
    const phase: "pickup" | "delivery" =
      (stopType ?? job.current_leg ?? "pickup").toLowerCase() === "pickup" ? "pickup" : "delivery";
    const scan: ScanProgress | undefined = phase === "pickup" ? job.scan_pickup : job.scan_delivery;
    const required = scan?.required ?? 0;
    onScanProgress(required <= 0 || Boolean(scan?.complete));
  }, [job, stopType, onScanProgress]);

  if (!orderId || !job) return null;

  const phase: "pickup" | "delivery" =
    (stopType ?? job.current_leg ?? "pickup").toLowerCase() === "pickup" ? "pickup" : "delivery";
  const scan: ScanProgress | undefined = phase === "pickup" ? job.scan_pickup : job.scan_delivery;
  const codCents = job.cod_amount_cents ?? 0;
  const showScan = (scan?.required ?? 0) > 0;
  const showCod = codCents > 0;

  if (!showScan && !showCod) return null;

  const locked = busy || Boolean(action);

  return (
    <View style={styles.wrap} testID="field-ops">
      <Text style={styles.title}>Field ops</Text>
      {showScan ? (
        <>
          <Text style={styles.meta} testID="scan-progress">
            {phase} scans {scan?.scanned ?? 0}/{scan?.required ?? 0}
            {scan?.complete ? " · complete" : ""}
          </Text>
          {(scan?.missing_suffixes?.length ?? 0) > 0 ? (
            <Text style={styles.meta}>Missing: {scan?.missing_suffixes?.join(", ")}</Text>
          ) : null}
          <TextInput
            style={styles.input}
            value={code}
            onChangeText={setCode}
            placeholder="PorterChain QR or tracking line"
            placeholderTextColor={colors.muted}
            autoCapitalize="characters"
            editable={!locked}
            testID="scan-input"
          />
          <PrimaryButton
            tone="ghost"
            label="Scan with camera"
            disabled={locked}
            testID="scan-camera"
            onPress={() => setScanOpen(true)}
          />
          <PrimaryButton
            tone="ghost"
            label={action === "scan" ? "Scanning…" : "Scan package"}
            disabled={locked || !code.trim()}
            testID="scan-submit"
            onPress={() => {
              setAction("scan");
              setNote(null);
              void scanPackage(orderId, code.trim(), phase)
                .then((result) => {
                  setCode("");
                  setNote(
                    result.complete
                      ? "All packages scanned"
                      : `Scanned ${result.scanned}/${result.required}`
                  );
                  return fetchJob(orderId).then(setJob);
                })
                .catch((err: unknown) => {
                  onError(err instanceof Error ? err.message : "scan_failed");
                })
                .finally(() => setAction(null));
            }}
          />
        </>
      ) : null}
      {showCod ? (
        <>
          <Text style={styles.meta} testID="cod-status">
            COD {formatCents(codCents)} · {(job.cod_status || "pending").replace(/_/g, " ")}
          </Text>
          <PrimaryButton
            label={action === "cod" ? "Opening…" : "Collect COD"}
            testID="cod-collect"
            disabled={
              locked ||
              job.cod_status === "collected" ||
              job.cod_status === "payout_processed" ||
              (showScan && !scan?.complete)
            }
            onPress={() => {
              setAction("cod");
              void codCheckout(orderId)
                .then(async (res) => {
                  if (res.checkout_url) {
                    await Linking.openURL(res.checkout_url);
                  }
                  setNote(res.mock ? "Mock COD checkout opened" : "COD payment link opened");
                  setJob(await fetchJob(orderId));
                })
                .catch((err: unknown) => {
                  onError(err instanceof Error ? err.message : "cod_failed");
                })
                .finally(() => setAction(null));
            }}
          />
        </>
      ) : null}
      {note ? <Text style={styles.note}>{note}</Text> : null}
      <BarcodeScannerModal
        visible={scanOpen}
        onClose={() => setScanOpen(false)}
        onScan={(value) => setCode(value)}
      />
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
  title: {
    ...typography.title,
    fontSize: 18,
    color: colors.primary,
  },
  meta: {
    ...typography.caption,
    color: colors.muted,
  },
  note: {
    ...typography.caption,
    color: colors.secondary,
    fontWeight: "600",
  },
  input: {
    ...typography.body,
    borderWidth: 1,
    borderColor: colors.muted,
    borderRadius: radius.lg,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    color: colors.primary,
    minHeight: 48,
  },
});
