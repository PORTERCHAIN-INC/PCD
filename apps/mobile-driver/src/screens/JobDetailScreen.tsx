import { useEffect, useState } from "react";
import { ScrollView, Text, StyleSheet, Linking } from "react-native";
import { colors, spacing, typography } from "@porterchain/mobile-theme";
import { acceptOrder, codCheckout, fetchJob, rejectOrder } from "../api";
import { formatCents, formatWhen, jobIsClosed } from "../format";
import { Card, CardTitle } from "../ui/Card";
import { PrimaryButton } from "../ui/PrimaryButton";
import { Screen } from "../ui/Screen";
import type { DriverJobDetail, DriverPackage, DriverProof } from "../types";

type Props = {
  orderId: string;
  onBack: () => void;
  onOpenWork: () => void;
};

function packageLabel(pkg: DriverPackage, index: number, total: number): string {
  const name = pkg.preset_label?.trim();
  if (name) {
    return `${name} · ${pkg.parcel_index ?? index + 1} of ${pkg.total_parcels ?? total}`;
  }
  if (pkg.tracking_suffix) {
    return `BOX ${pkg.parcel_index ?? index + 1} of ${pkg.total_parcels ?? total}`;
  }
  return pkg.package_type ?? "Package";
}

function proofLine(proof: DriverProof): string {
  const kind = (proof.type || "proof").replace(/_/g, " ");
  const value = proof.value ? ` — ${proof.value.slice(0, 80)}` : "";
  return `${kind}${value}`;
}

export function JobDetailScreen({ orderId, onBack, onOpenWork }: Props) {
  const [job, setJob] = useState<DriverJobDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void fetchJob(orderId)
      .then((next) => {
        if (!cancelled) setJob(next);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "job_failed");
      });
    return () => {
      cancelled = true;
    };
  }, [orderId]);

  const closed = job ? jobIsClosed(job) : false;
  const canAssign = Boolean(job && !job.is_current_job && !closed);
  const packages = job?.packages ?? [];
  const timeline = job?.timeline ?? [];
  const proofs = [
    ...(job?.photos ?? []),
    ...(job?.signatures ?? []),
    ...(job?.documents ?? []),
    ...(job?.proof_of_delivery?.proofs ?? []),
  ];
  const codPending =
    (job?.cod_amount_cents ?? 0) > 0 &&
    job?.cod_status !== "collected" &&
    job?.cod_status !== "payout_processed";

  return (
    <Screen testID="mobile-job-detail">
      <Text style={styles.title}>Job</Text>
      <Text style={styles.meta}>{orderId}</Text>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <ScrollView contentContainerStyle={styles.list} showsVerticalScrollIndicator={false}>
        {job ? (
          <>
            <Card>
              <CardTitle>{job.order_number}</CardTitle>
              <Text style={styles.body}>{job.tracking_number}</Text>
              {job.merchant?.company_name ? (
                <Text style={styles.meta}>{job.merchant.company_name}</Text>
              ) : null}
              <Text style={styles.body}>{job.pickup_address || "Pickup —"}</Text>
              <Text style={styles.body}>{job.delivery_address || "Dropoff —"}</Text>
              <Text style={styles.meta}>
                {(job.status || job.state || "assigned").replace(/_/g, " ")}
                {job.otp_required ? " · OTP required" : ""}
              </Text>
              {job.delivery_completed_at ? (
                <Text style={styles.meta}>Delivered {formatWhen(job.delivery_completed_at)}</Text>
              ) : job.pickup_completed_at ? (
                <Text style={styles.meta}>Picked up {formatWhen(job.pickup_completed_at)}</Text>
              ) : null}
              {(job.cod_amount_cents ?? 0) > 0 ? (
                <Text style={styles.meta}>
                  COD {formatCents(job.cod_amount_cents)} ·{" "}
                  {(job.cod_status || "pending").replace(/_/g, " ")}
                </Text>
              ) : null}
              <Text style={styles.meta}>
                Pickup scans {job.scan_pickup?.scanned ?? 0}/{job.scan_pickup?.required ?? 0}
              </Text>
              <Text style={styles.meta}>
                Delivery scans {job.scan_delivery?.scanned ?? 0}/{job.scan_delivery?.required ?? 0}
              </Text>
              {job.special_instructions ? (
                <Text style={styles.body}>{job.special_instructions}</Text>
              ) : null}
              {(job.delivery_attempts ?? 0) > 0 ? (
                <Text style={styles.meta}>
                  Attempts {job.delivery_attempts} of {job.max_delivery_attempts ?? 2}
                </Text>
              ) : null}
            </Card>

            {job.declared_value_cents ? (
              <Text style={styles.meta}>
                Declared value ${(job.declared_value_cents / 100).toFixed(2)}
              </Text>
            ) : null}
            {job.booking_mode === "vehicle" ? (
              <Text style={styles.meta}>Whole vehicle · {job.vehicle_class || "vehicle"}</Text>
            ) : null}
            {job.booking_mode === "vehicle" ? null : (
              <Card testID="job-packages">
                <CardTitle>Packages</CardTitle>
                {job.packages_error ? (
                  <Text style={styles.error}>Package list unavailable — refresh.</Text>
                ) : packages.length === 0 ? (
                  <Text style={styles.meta}>No package details on file</Text>
                ) : (
                  packages.map((pkg, i) => (
                    <Text key={String(pkg.id ?? pkg.tracking_suffix ?? i)} style={styles.body}>
                      {packageLabel(pkg, i, packages.length)}
                      {pkg.tracking_suffix ? ` · ${pkg.tracking_suffix}` : ""}
                      {pkg.scanned_pickup ? " · pickup scanned" : ""}
                      {pkg.scanned_delivery ? " · delivered" : ""}
                      {pkg.status ? ` · ${pkg.status.replace(/_/g, " ")}` : ""}
                      {pkg.weight_kg != null ? ` · ${pkg.weight_kg} kg` : ""}
                      {pkg.instructions ? ` · ${pkg.instructions}` : ""}
                    </Text>
                  ))
                )}
              </Card>
            )}

            <Card testID="job-timeline">
              <CardTitle>Timeline</CardTitle>
              {timeline.length === 0 ? (
                <Text style={styles.meta}>No events yet</Text>
              ) : (
                timeline.map((ev, i) => (
                  <Text key={`${ev.event_type}-${ev.occurred_at ?? i}`} style={styles.body}>
                    {ev.label}
                    {ev.to_state ? ` → ${ev.to_state}` : ""}
                    {ev.occurred_at ? ` · ${formatWhen(ev.occurred_at)}` : ""}
                  </Text>
                ))
              )}
            </Card>

            <Card testID="job-pod">
              <CardTitle>Proof of delivery</CardTitle>
              <Text style={styles.meta}>
                {job.proof_of_delivery?.completed ? "POD complete" : "POD not complete"}
                {job.proof_of_delivery?.otp_verified ? " · OTP verified" : ""}
              </Text>
              {proofs.length === 0 ? (
                <Text style={styles.meta}>No photos or signatures on file</Text>
              ) : (
                proofs.map((proof, i) => (
                  <Text key={`${proof.type ?? "proof"}-${i}`} style={styles.body}>
                    {proofLine(proof)}
                  </Text>
                ))
              )}
            </Card>
          </>
        ) : (
          <Text style={styles.meta}>{error ? "Could not load job" : "Loading job…"}</Text>
        )}
      </ScrollView>
      {canAssign ? (
        <PrimaryButton
          label={busy === "accept" ? "Accepting…" : "Accept job"}
          disabled={Boolean(busy)}
          onPress={() => {
            setBusy("accept");
            void acceptOrder(orderId)
              .then(() => onOpenWork())
              .catch((err: unknown) => {
                setError(err instanceof Error ? err.message : "accept_failed");
              })
              .finally(() => setBusy(null));
          }}
        />
      ) : null}
      {canAssign ? (
        <PrimaryButton
          tone="ghost"
          label="Decline"
          disabled={Boolean(busy)}
          onPress={() => {
            setBusy("reject");
            void rejectOrder(orderId)
              .then(onBack)
              .catch((err: unknown) => {
                setError(err instanceof Error ? err.message : "reject_failed");
              })
              .finally(() => setBusy(null));
          }}
        />
      ) : null}
      {codPending ? (
        <PrimaryButton
          tone="ghost"
          label={busy === "cod" ? "Opening…" : "Collect COD"}
          disabled={Boolean(busy)}
          onPress={() => {
            setBusy("cod");
            void codCheckout(orderId)
              .then(async (res) => {
                if (res.checkout_url) await Linking.openURL(res.checkout_url);
              })
              .catch((err: unknown) => {
                setError(err instanceof Error ? err.message : "cod_failed");
              })
              .finally(() => setBusy(null));
          }}
        />
      ) : null}
      <PrimaryButton tone="ghost" label="Back to work" onPress={onOpenWork} />
      <PrimaryButton tone="ghost" label="Close" onPress={onBack} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { ...typography.title, fontSize: 28, color: colors.primary },
  body: { ...typography.body, color: colors.primary },
  meta: { ...typography.caption, color: colors.muted },
  error: { ...typography.caption, color: colors.danger },
  list: { gap: spacing.md, paddingBottom: spacing.md },
});
