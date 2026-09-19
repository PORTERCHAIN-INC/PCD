import { useEffect, useState } from "react";
import { ScrollView, Text, StyleSheet, Linking } from "react-native";
import { colors, spacing, typography } from "@porterchain/mobile-theme";
import { acceptOrder, codCheckout, fetchJob, rejectOrder } from "../api";
import { formatCents } from "../format";
import { Card, CardTitle } from "../ui/Card";
import { PrimaryButton } from "../ui/PrimaryButton";
import { Screen } from "../ui/Screen";
import type { DriverJobDetail } from "../types";

type Props = {
  orderId: string;
  onBack: () => void;
  onOpenWork: () => void;
};

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

  return (
    <Screen testID="mobile-job-detail">
      <Text style={styles.title}>Job</Text>
      <Text style={styles.meta}>{orderId}</Text>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <ScrollView contentContainerStyle={styles.list} showsVerticalScrollIndicator={false}>
        {job ? (
          <Card>
            <CardTitle>{job.order_number}</CardTitle>
            <Text style={styles.body}>{job.tracking_number}</Text>
            <Text style={styles.body}>{job.pickup_address || "Pickup —"}</Text>
            <Text style={styles.body}>{job.delivery_address || "Dropoff —"}</Text>
            <Text style={styles.meta}>
              {(job.status || job.state || "assigned").replace(/_/g, " ")}
              {job.otp_required ? " · OTP required" : ""}
            </Text>
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
          </Card>
        ) : (
          <Text style={styles.meta}>Loading job…</Text>
        )}
      </ScrollView>
      {job && !job.is_current_job ? (
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
      {job && !job.is_current_job ? (
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
      {(job?.cod_amount_cents ?? 0) > 0 ? (
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
