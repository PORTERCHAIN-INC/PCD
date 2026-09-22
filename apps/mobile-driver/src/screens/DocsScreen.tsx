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
import { ScreenHeader } from "../ui/ScreenHeader";
import type { DriverDocument, DriverVehicle, InsuranceStatus, TrainingModule } from "../types";

function docStatusLabel(doc: DriverDocument): string {
  if (doc.verified || doc.status === "verified") return "Verified";
  if (doc.status === "pending_review") return "Waiting for PorterChain review";
  if (doc.status === "rejected") return "Needs a new photo";
  if (doc.status === "expired") return "Expired";
  if (!doc.url || doc.status === "missing") return "Upload a photo";
  return (doc.status || "missing").replace(/_/g, " ");
}

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

  const rows: DriverDocument[] = (
    docs.length > 0
      ? docs
      : FALLBACK_DOC_TYPES.map((item) => ({
          type: item.type,
          label: item.label,
          status: "missing",
          verified: false,
          url: null,
          expires_at: null,
        }))
  ).filter(
    (doc) =>
      ["license", "insurance", "vehicle_registration", "abstract"].includes(doc.type) ||
      doc.verified ||
      Boolean(doc.url)
  );

  return (
    <Screen testID="mobile-docs" includeBottomSafeArea={false}>
      <ScreenHeader
        title="Documents"
        lede="License, insurance, vehicle, and training — capture on device and sync."
      />
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
          <Text
            style={[
              styles.status,
              insurance?.verified || insurance?.insurance_verified ? styles.ok : styles.warn,
            ]}
          >
            {insurance?.verified || insurance?.insurance_verified
              ? "Verified"
              : (insurance?.status || "not_on_file").replace(/_/g, " ")}
          </Text>
          {insurance?.status === "expired" ? (
            <Text style={styles.warn}>Expired — cannot work until you upload a current file.</Text>
          ) : null}
          {insurance?.expires_at ? (
            <Text style={styles.meta}>Expires {formatWhen(insurance.expires_at)}</Text>
          ) : null}
        </Card>

        {rows.map((doc) => (
          <Card key={doc.type}>
            <Text style={styles.label}>{doc.label}</Text>
            <Text style={[styles.status, doc.verified ? styles.ok : styles.warn]}>
              {docStatusLabel(doc)}
            </Text>
            {doc.status === "rejected" && doc.rejection_reason ? (
              <Text style={styles.warn}>{doc.rejection_reason}</Text>
            ) : null}
            {doc.status === "expired" ? (
              <Text style={styles.warn}>
                Expired — cannot work until you upload a current file.
              </Text>
            ) : null}
            {doc.expires_at ? (
              <Text style={styles.meta}>Expires {formatWhen(doc.expires_at)}</Text>
            ) : null}
            {doc.url && !doc.url.includes("porterchain.local") ? (
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
