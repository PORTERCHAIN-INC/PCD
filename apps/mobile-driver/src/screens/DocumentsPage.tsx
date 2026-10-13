/**
 * Documents + vehicle: status, expiry and warnings at a glance (from cache, instantly).
 * Tap a document to expand it inline: take a photo, pick one, or choose a file; it's
 * auto-compressed and sent; the row flips to "In review" at once (optimistic).
 */
import { useState } from "react";
import { StyleSheet, Text, TextInput, View } from "react-native";
import type { DriverDocument, DriverVehicle } from "../api";
import { useDocuments, useUploadDocument, useVehicle } from "../data/queries";
import { docHealth, docLine, sortDocs, type DocHealth } from "../docs";
import { humanError } from "../errorCopy";
import { haptic } from "../haptics";
import { useT } from "../i18n";
import { captureDocumentDataUrl } from "../pod";
import { Button } from "../ui/kit";
import { PressScale, Rise, Skeleton } from "../ui/motion";
import { Section } from "../ui/settings/rows";
import { Sheet } from "../ui/Sheet";
import { color, radius, space } from "../ui/theme";
import { toast } from "../ui/toast";
import { UpdatedAgo } from "../ui/UpdatedAgo";

export function DocumentsPage({ visible, onClose }: { visible: boolean; onClose: () => void }) {
  return (
    <Sheet
      visible={visible}
      title="Documents"
      kicker="Licence · insurance · vehicle"
      onClose={onClose}
      testID="page-documents"
    >
      <DocumentsBody />
    </Sheet>
  );
}

const DOT: Record<DocHealth, string> = {
  ok: color.primary,
  review: color.infoInk,
  expiring: color.warnInk,
  expired: color.danger,
  rejected: color.danger,
  missing: color.danger,
};

export function DocumentsBody({ now = Date.now() }: { now?: number }) {
  const t = useT();
  const docs = useDocuments();
  const vehicle = useVehicle();
  const [open, setOpen] = useState<string | null>(null);
  const list = sortDocs(docs.data?.documents ?? [], now);
  const firstLoad = docs.data === undefined && docs.isPending;

  return (
    <View style={st.wrap}>
      <UpdatedAgo at={docs.dataUpdatedAt} fetching={docs.isFetching} />
      <VehicleCard
        v={vehicle.data?.vehicle ?? null}
        loading={vehicle.data === undefined && vehicle.isPending}
        label={t("vehicle")}
      />
      <Section title={t("documents").toUpperCase()} testID="docs-list">
        {firstLoad
          ? [0, 1, 2].map((i) => (
              <View key={i} style={st.row}>
                <Skeleton width="60%" height={18} />
              </View>
            ))
          : list.map((d) => (
              <DocRow
                key={d.type}
                d={d}
                now={now}
                open={open === d.type}
                onToggle={() => setOpen((o) => (o === d.type ? null : d.type))}
              />
            ))}
      </Section>
      {docs.isError && !docs.data ? (
        <Text style={st.err}>Couldn't load documents. Pull to retry when you have signal.</Text>
      ) : null}
    </View>
  );
}

function VehicleCard({
  v,
  loading,
  label,
}: {
  v: DriverVehicle | null;
  loading: boolean;
  label: string;
}) {
  const name = v ? [v.year, v.make, v.model].filter(Boolean).join(" ") : "";
  const plate = v?.plate ?? v?.license_plate;
  return (
    <Section title={label.toUpperCase()} testID="vehicle-card">
      <View style={st.vehicle}>
        {loading ? (
          <Skeleton width="70%" height={22} />
        ) : v ? (
          <>
            <Text style={st.vName}>{name || "Vehicle on file"}</Text>
            <View style={st.chips}>
              {plate ? <Chip text={plate} mono /> : null}
              {v.color ? <Chip text={v.color} /> : null}
              {v.vehicle_class ? <Chip text={v.vehicle_class} /> : null}
              {v.capacity_kg ? <Chip text={`${v.capacity_kg} kg`} /> : null}
              {(v.capabilities ?? []).map((c) => (
                <Chip key={c} text={c.replace(/_/g, " ")} />
              ))}
            </View>
          </>
        ) : (
          <Text style={st.sub}>No vehicle on file. Dispatch adds it after your inspection.</Text>
        )}
      </View>
    </Section>
  );
}

function DocRow({
  d,
  now,
  open,
  onToggle,
}: {
  d: DriverDocument;
  now: number;
  open: boolean;
  onToggle: () => void;
}) {
  const h = docHealth(d, now);
  const upload = useUploadDocument();
  const [expiry, setExpiry] = useState(d.expires_at?.slice(0, 10) ?? "");
  const [busy, setBusy] = useState(false);
  const expiryOk = expiry === "" || /^\d{4}-\d{2}-\d{2}$/.test(expiry);
  const pick = (source: "camera" | "library" | "file") => {
    if (!expiryOk)
      return toast.show("warn", "Check the expiry date", "Use YYYY-MM-DD, e.g. 2027-03-31.");
    setBusy(true);
    void captureDocumentDataUrl(source)
      .then((file_url) => {
        upload.mutate({ doc_type: d.type, file_url, expires_at: expiry || null });
        onToggle();
      })
      .catch((e: Error) => {
        if (e.message !== "photo_cancelled")
          toast.show("danger", "Couldn't use that photo", humanError(e.message));
      })
      .finally(() => setBusy(false));
  };
  return (
    <View testID={`doc-${d.type}`}>
      <PressScale
        accessibilityRole="button"
        accessibilityState={{ expanded: open }}
        accessibilityLabel={`${d.label}. ${docLine(d, now)}`}
        onPress={() => {
          haptic.tap();
          onToggle();
        }}
        style={st.docRow}
      >
        <View style={[st.dot, { backgroundColor: DOT[h] }]} />
        <View style={st.flex}>
          <Text style={st.docLabel}>{d.label}</Text>
          <Text style={[st.docLine, { color: h === "ok" ? color.inkMuted : DOT[h] }]}>
            {docLine(d, now)}
          </Text>
        </View>
        <Text style={st.action}>{h === "missing" ? "Upload" : open ? "Close" : "Replace"}</Text>
      </PressScale>
      {open ? (
        <Rise>
          <View style={st.expand}>
            <Text style={st.fieldLabel}>Expiry date</Text>
            <TextInput
              value={expiry}
              onChangeText={setExpiry}
              placeholder="YYYY-MM-DD"
              placeholderTextColor={color.inkFaint}
              keyboardType="numbers-and-punctuation"
              maxLength={10}
              style={[st.input, !expiryOk && st.inputBad]}
              accessibilityLabel={`${d.label} expiry date`}
            />
            <Button
              tone="primary"
              label={h === "missing" ? "Take a photo" : "Retake with camera"}
              busy={busy}
              onPress={() => pick("camera")}
              testID={`doc-camera-${d.type}`}
            />
            <View style={st.two}>
              <View style={st.flex}>
                <Button label="Photos" disabled={busy} onPress={() => pick("library")} />
              </View>
              <View style={st.flex}>
                <Button label="Files" disabled={busy} onPress={() => pick("file")} />
              </View>
            </View>
            <Text style={st.sub}>Flat, all four corners, no glare. We shrink it to send fast.</Text>
          </View>
        </Rise>
      ) : null}
    </View>
  );
}

function Chip({ text, mono }: { text: string; mono?: boolean }) {
  return (
    <View style={st.chip}>
      <Text style={[st.chipText, mono && st.mono]}>{text}</Text>
    </View>
  );
}

const st = StyleSheet.create({
  wrap: { gap: space.lg },
  row: { minHeight: 56, justifyContent: "center", paddingHorizontal: space.lg },
  vehicle: { padding: space.lg, gap: space.sm },
  vName: { fontSize: 20, lineHeight: 26, fontWeight: "800", color: color.ink },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: space.sm },
  chip: {
    backgroundColor: color.surface2,
    borderRadius: radius.pill,
    paddingHorizontal: space.md,
    paddingVertical: 5,
  },
  chipText: { fontSize: 13, fontWeight: "700", color: color.inkMuted, textTransform: "capitalize" },
  mono: {
    fontVariant: ["tabular-nums"],
    letterSpacing: 1,
    color: color.ink,
    textTransform: "uppercase",
  },
  sub: { fontSize: 13, lineHeight: 18, color: color.inkMuted },
  err: { fontSize: 14, color: color.danger },
  expand: {
    gap: space.sm,
    padding: space.lg,
    paddingTop: space.xs,
    backgroundColor: color.surface,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: color.border,
  },
  fieldLabel: { fontSize: 13, fontWeight: "800", color: color.inkMuted, letterSpacing: 1 },
  input: {
    minHeight: 48,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: color.border,
    color: color.ink,
    fontSize: 18,
    paddingHorizontal: space.md,
    fontVariant: ["tabular-nums"],
  },
  inputBad: { borderColor: color.danger },
  two: { flexDirection: "row", gap: space.sm },
  flex: { flex: 1 },
  docRow: {
    minHeight: 60,
    flexDirection: "row",
    alignItems: "center",
    gap: space.md,
    paddingHorizontal: space.lg,
    paddingVertical: space.sm + 2,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: color.border,
  },
  dot: { width: 10, height: 10, borderRadius: 5 },
  docLabel: { fontSize: 16, lineHeight: 21, fontWeight: "700", color: color.ink },
  docLine: { fontSize: 13, lineHeight: 18, fontWeight: "600", marginTop: 2 },
  action: { fontSize: 14, fontWeight: "800", color: color.primary },
});
