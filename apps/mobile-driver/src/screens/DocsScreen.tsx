import { useCallback, useEffect, useState } from "react";
import { Linking, ScrollView, Text, View, StyleSheet } from "react-native";
import { colors, spacing, typography } from "@porterchain/mobile-theme";
import {
  completeTraining,
  fetchDocuments,
  fetchInsurance,
  fetchTraining,
  fetchVehicle,
} from "../api";
import {
  FALLBACK_DOC_TYPES,
  captureAndUploadDocument,
  captureAndUploadVehiclePhoto,
} from "../docsUpload";
import { formatWhen } from "../format";
import { Card, CardTitle } from "../ui/Card";
import { PrimaryButton } from "../ui/PrimaryButton";
import { Screen } from "../ui/Screen";
import type { DriverDocument, DriverVehicle, InsuranceStatus, TrainingModule } from "../types";

export function DocsScreen() {
  const [docs, setDocs] = useState<DriverDocument[]>([]);
  const [vehicle, setVehicle] = useState<DriverVehicle | null>(null);
  const [insurance, setInsurance] = useState<InsuranceStatus | null>(null);
  const [modules, setModules] = useState<TrainingModule[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [payload, veh, ins, train] = await Promise.all([
        fetchDocuments(),
        fetchVehicle().catch(() => ({ vehicle: null, vehicles: [] })),
        fetchInsurance().catch(() => null),
        fetchTraining().catch(() => ({ modules: [] as TrainingModule[] })),
      ]);
      setDocs(payload.documents ?? []);
      setVehicle(veh.vehicle ?? veh.vehicles?.[0] ?? null);
      setInsurance(ins);
      setModules(train.modules ?? []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "documents_failed");
    }
  }, []);

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

  async function uploadVehicle() {
    setBusy("vehicle_photo");
    setError(null);
    try {
      await captureAndUploadVehiclePhoto();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "vehicle_photo_failed");
    } finally {
      setBusy(null);
    }
  }

  const rows: DriverDocument[] =
    docs.length > 0
      ? docs
      : FALLBACK_DOC_TYPES.map((item) => ({
          type: item.type,
          label: item.label,
          status: "missing",
          verified: false,
          url: null,
          expires_at: null,
        }));

  return (
    <Screen testID="mobile-docs">
      <Text style={styles.title}>Documents</Text>
      <Text style={styles.lede}>
        License, insurance, vehicle, and training — capture on device and sync.
      </Text>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <ScrollView
        style={styles.flex}
        contentContainerStyle={styles.list}
        showsVerticalScrollIndicator={false}
      >
        <Card>
          <CardTitle>Vehicle</CardTitle>
          <Text style={styles.label}>
            {vehicle
              ? `${vehicle.make_model || vehicle.vehicle_class || "Vehicle"} · ${vehicle.plate_number || "—"}`
              : "No active vehicle on file"}
          </Text>
          <PrimaryButton
            tone="ghost"
            label={busy === "vehicle_photo" ? "Uploading…" : "Upload vehicle photo"}
            disabled={Boolean(busy)}
            onPress={() => void uploadVehicle()}
          />
        </Card>

        <Card>
          <CardTitle>Insurance</CardTitle>
          <Text style={styles.status}>
            {(insurance?.status || "unknown").replace(/_/g, " ")}
            {insurance?.verified ? " · verified" : ""}
          </Text>
          {insurance?.expires_at ? (
            <Text style={styles.meta}>Expires {formatWhen(insurance.expires_at)}</Text>
          ) : null}
        </Card>

        {rows.map((doc) => (
          <Card key={doc.type}>
            <Text style={styles.label}>{doc.label}</Text>
            <Text style={[styles.status, doc.verified ? styles.ok : styles.warn]}>
              {doc.verified ? "Verified" : (doc.status || "missing").replace(/_/g, " ")}
            </Text>
            {doc.expires_at ? (
              <Text style={styles.meta}>Expires {formatWhen(doc.expires_at)}</Text>
            ) : null}
            {doc.url ? (
              <PrimaryButton
                tone="ghost"
                label="Open file"
                onPress={() => void Linking.openURL(doc.url as string)}
              />
            ) : null}
            <PrimaryButton
              tone="ghost"
              label={busy === doc.type ? "Uploading…" : doc.url ? "Replace photo" : "Upload photo"}
              disabled={Boolean(busy)}
              onPress={() => void upload(doc.type)}
            />
          </Card>
        ))}

        <Card>
          <CardTitle>Training</CardTitle>
          {modules.map((mod) => (
            <View key={mod.id} style={styles.module}>
              <Text style={styles.label}>{mod.title || mod.name || mod.id}</Text>
              <Text style={styles.meta}>
                {mod.completed || mod.status === "completed" ? "Completed" : "Incomplete"}
              </Text>
              {!mod.completed && mod.status !== "completed" ? (
                <PrimaryButton
                  tone="ghost"
                  label={busy === mod.id ? "Saving…" : "Mark complete"}
                  disabled={Boolean(busy)}
                  onPress={() => {
                    setBusy(mod.id);
                    void completeTraining(mod.id)
                      .then(load)
                      .catch((err: unknown) => {
                        setError(err instanceof Error ? err.message : "training_failed");
                      })
                      .finally(() => setBusy(null));
                  }}
                />
              ) : null}
            </View>
          ))}
          {modules.length === 0 ? <Text style={styles.meta}>No training modules.</Text> : null}
        </Card>
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { ...typography.title, fontSize: 28, color: colors.primary },
  lede: { ...typography.caption, color: colors.muted },
  error: { ...typography.caption, color: colors.danger },
  flex: { flex: 1 },
  list: { gap: spacing.md, paddingBottom: spacing.xl },
  label: { ...typography.title, color: colors.primary },
  status: { ...typography.body, fontWeight: "600", color: colors.primary },
  ok: { color: colors.success },
  warn: { color: colors.danger },
  meta: { ...typography.caption, color: colors.muted },
  module: { gap: spacing.xs, marginTop: spacing.sm },
});
