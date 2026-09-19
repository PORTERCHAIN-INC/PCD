import { useCallback, useEffect, useState } from "react";
import { ScrollView, Text, StyleSheet } from "react-native";
import { colors, spacing, typography } from "@porterchain/mobile-theme";
import { fetchOnboarding } from "../api";
import { captureAndUploadDocument, uploadTypeForOnboardingStep } from "../docsUpload";
import { Card } from "../ui/Card";
import { PrimaryButton } from "../ui/PrimaryButton";
import { Screen } from "../ui/Screen";
import type { DriverOnboarding } from "../types";

type Props = {
  onReady: () => void;
  onSkipDev?: () => void;
  allowSkip?: boolean;
};

export function OnboardingScreen({ onReady, onSkipDev, allowSkip }: Props) {
  const [status, setStatus] = useState<DriverOnboarding | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const next = await fetchOnboarding();
      setStatus(next);
      if (next.ready) onReady();
    } catch (err) {
      setError(err instanceof Error ? err.message : "onboarding_failed");
    }
  }, [onReady]);

  useEffect(() => {
    void load();
  }, [load]);

  async function upload(docType: string) {
    setBusy(docType);
    setError(null);
    try {
      await captureAndUploadDocument(docType);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "upload_failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <Screen testID="mobile-onboarding">
      <Text style={styles.title}>Get road-ready</Text>
      <Text style={styles.lede}>
        Finish compliance before going on duty. Uploads go to Porterchain — Fleetbase stays
        logistics-only.
      </Text>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <ScrollView
        style={styles.flex}
        contentContainerStyle={styles.list}
        showsVerticalScrollIndicator={false}
      >
        {(status?.steps ?? []).map((step) => {
          const docType = uploadTypeForOnboardingStep(step.id);
          const missing =
            step.id === "documents_uploaded"
              ? step.missing?.length
                ? step.missing
                : ["license", "insurance", "vehicle_registration"]
              : docType
                ? [docType]
                : [];
          return (
            <Card key={step.id}>
              <Text style={styles.label}>{step.label}</Text>
              <Text style={[styles.status, step.complete ? styles.ok : styles.warn]}>
                {step.complete ? "Complete" : (step.status || "pending").replace(/_/g, " ")}
              </Text>
              <Text style={styles.meta}>{step.description}</Text>
              {!step.complete
                ? missing.map((type) => (
                    <PrimaryButton
                      key={type}
                      tone="ghost"
                      label={
                        busy === type
                          ? `Uploading ${type.replace(/_/g, " ")}…`
                          : `Upload ${type.replace(/_/g, " ")}`
                      }
                      disabled={Boolean(busy)}
                      onPress={() => void upload(type)}
                    />
                  ))
                : null}
            </Card>
          );
        })}
        {status && !status.ready ? (
          <Text style={styles.meta} testID="onboarding-blockers">
            Blockers: {(status.blockers ?? []).join(", ") || "waiting on verification"}
          </Text>
        ) : null}
      </ScrollView>
      <PrimaryButton
        testID="onboarding-refresh"
        tone="ghost"
        label="Refresh status"
        disabled={Boolean(busy)}
        onPress={() => void load()}
      />
      {status?.ready ? (
        <PrimaryButton testID="onboarding-continue" label="Continue to field" onPress={onReady} />
      ) : null}
      {allowSkip && onSkipDev ? (
        <PrimaryButton
          testID="onboarding-skip-dev"
          tone="ghost"
          label="Dev skip onboarding"
          onPress={onSkipDev}
        />
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { ...typography.title, fontSize: 28, color: colors.primary },
  lede: { ...typography.caption, color: colors.muted },
  error: { ...typography.caption, color: colors.danger },
  flex: { flex: 1 },
  list: { gap: spacing.md, paddingBottom: spacing.md },
  label: { ...typography.title, color: colors.primary },
  status: { ...typography.body, fontWeight: "600" },
  ok: { color: colors.success },
  warn: { color: colors.danger },
  meta: { ...typography.caption, color: colors.muted },
});
