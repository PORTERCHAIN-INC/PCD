/** Bulk batches: pickup (list, spot check, count+photo, docs, must-read notes, handover), deliver by building,
 * driver-to-driver handover and leftovers. Gates and copy come from the vendored driver-flows package. */
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  adviceText,
  blockMessage,
  cardCopy,
  handlingLabels,
  type ScanAdvice,
} from "@porterchain/driver-flows";
import { batchApi, mediaApi, safetyApi } from "../api";
import { capturePodPhotoDataUrl } from "../pod";
import { SignaturePad } from "../ui/SignaturePad";
import { buildingBlockers, leftovers, pickupBlockers, type PickupState } from "../batches";
import { Button } from "../ui/kit";
import { InputRow, Row, Section } from "../ui/settings/rows";
import { Sheet } from "../ui/Sheet";
import { color, space } from "../ui/theme";
import { toast } from "../ui/toast";
import { loadLocation, readPosition } from "../location";

/** Camera → Garage key. Proof keys come from the server only (no invented local keys). */
async function snapKey(): Promise<string> {
  return (await mediaApi.photoDataUrl(await capturePodPhotoDataUrl())).key;
}

function PhotoRow({
  label,
  value,
  onKey,
  testID,
}: {
  label: string;
  value: string;
  onKey: (k: string) => void;
  testID?: string;
}) {
  return (
    <Row
      label={label}
      value={value ? "✓" : "Take photo"}
      testID={testID}
      onPress={() =>
        void snapKey().then(onKey, (e: Error) => toast.show("danger", "Photo not saved", e.message))
      }
    />
  );
}

function SignRow({
  label,
  signer,
  onKey,
}: {
  label: string;
  signer: string;
  onKey: (k: string) => void;
}) {
  const [png, setPng] = useState("");
  const [saved, setSaved] = useState(false);
  return (
    <View>
      <Text style={st.h}>{label}</Text>
      <SignaturePad
        onChange={(v) => {
          setPng(v);
          setSaved(false);
        }}
      />
      <Button
        label={saved ? "Signature saved ✓" : "Save signature"}
        disabled={!png || signer.trim().length < 2 || saved}
        onPress={() =>
          void mediaApi.signature(png, signer).then(
            (r) => {
              setSaved(true);
              onKey(r.key);
            },
            (e: Error) => toast.show("danger", "Signature not saved", e.message)
          )
        }
      />
    </View>
  );
}

export function BatchesPage({ visible, onClose }: { visible: boolean; onClose: () => void }) {
  return (
    <Sheet
      visible={visible}
      title="Batches"
      kicker="Bulk pickup · handover · building drops"
      onClose={onClose}
      testID="page-batches"
    >
      <BatchesBody />
    </Sheet>
  );
}

export function BatchesBody() {
  const routes = useQuery({ queryKey: ["batch-routes"], queryFn: () => batchApi.routes() });
  const r = routes.data?.items?.[0];
  if (!r) return <Text style={st.muted}>No batch routes assigned.</Text>;
  return (
    <View style={st.wrap}>
      <Text style={st.h}>
        Route {r.route_no} · wave {r.wave} · {r.status}
      </Text>
      {r.status === "planned" ? <PickupBody routeId={r.id} /> : <DeliverBody routeId={r.id} />}
      <HandoverBody routeId={r.id} />
      <SafetyBody routeId={r.id} />
    </View>
  );
}

function PickupBody({ routeId }: { routeId: string }) {
  const qc = useQueryClient();
  const v = useQuery({
    queryKey: ["batch-pickup", routeId],
    queryFn: () => batchApi.pickup(routeId),
  });
  const [s, setS] = useState<PickupState>({ scanned: [], acked: [] });
  const [code, setCode] = useState("");
  const [advice, setAdvice] = useState<ScanAdvice | null>(null);
  const [shipper, setShipper] = useState("");
  const [seal, setSeal] = useState("");
  const [photoKey, setPhotoKey] = useState("");
  const [docKey, setDocKey] = useState("");
  const [sigKey, setSigKey] = useState("");
  if (!v.data) return <Text style={st.muted}>Loading…</Text>;
  const view = v.data;
  const blockers = pickupBlockers(view, s);
  const refresh = () => qc.invalidateQueries({ queryKey: ["batch-pickup", routeId] });
  return (
    <View>
      {view.documents.reminders.map((m) => (
        <Text key={m} style={st.warn}>
          {m}
        </Text>
      ))}
      <Section title="INSTRUCTIONS">
        {view.instructions.items.map((i) => (
          <Row
            key={i.id}
            label={i.text}
            sub={i.priority === "must_read" ? "Must read" : i.priority}
            tone={
              i.priority === "must_read" && !s.acked.includes(i.id) && !i.acknowledged
                ? "accent"
                : undefined
            }
            onPress={
              i.priority === "must_read"
                ? () =>
                    void batchApi.ack(i.id).then(() => setS({ ...s, acked: [...s.acked, i.id] }))
                : undefined
            }
            testID={`instr-${i.id}`}
          />
        ))}
      </Section>
      <Section title={`${cardCopy("batch_parcel_list").title.toUpperCase()} (${view.expected})`}>
        {view.parcels.map((p) => (
          <Row
            key={p.id}
            label={`#${p.load_position} ${p.barcode}${s.scanned.includes(p.barcode) ? " ✓" : ""}`}
            sub={`${p.address}${p.unit ? ` u${p.unit}` : ""} ${handlingLabels(p.handling).join(", ")}${view.spot_sample.includes(p.barcode) ? " · spot check" : ""}`}
          />
        ))}
      </Section>
      <InputRow label="Scan code" value={code} onChange={setCode} testID="batch-scan" />
      <Button
        label="Scan"
        onPress={() =>
          void batchApi.scan(routeId, code, "pickup", s.scanned).then((a) => {
            setAdvice(a);
            if (a.barcode && !s.scanned.includes(a.barcode))
              setS({ ...s, scanned: [...s.scanned, a.barcode] });
            setCode("");
          })
        }
      />
      {advice ? <Text style={st.h}>{adviceText(advice)}</Text> : null}
      <InputRow
        label="Count"
        value={s.counted == null ? "" : String(s.counted)}
        onChange={(t) => setS({ ...s, counted: Number(t) })}
        testID="batch-count"
      />
      <PhotoRow
        label={cardCopy("count_photo").button}
        value={photoKey}
        testID="batch-photo"
        onKey={(k) => {
          setPhotoKey(k);
          setS({ ...s, photo: true });
        }}
      />
      <Row
        label={cardCopy("count_exception").title}
        value={s.countException ? "✓" : ""}
        onPress={() => setS({ ...s, countException: !s.countException })}
      />
      {view.documents.items.length ? (
        <Section title="PICKUP DOCUMENTS">
          <InputRow
            label="Shipper name"
            value={shipper}
            onChange={setShipper}
            testID="doc-shipper"
          />
          <InputRow label="Seal number" value={seal} onChange={setSeal} testID="doc-seal" />
          <PhotoRow label="Document photo" value={docKey} onKey={setDocKey} testID="doc-photo" />
          <SignRow label="Shipper signature" signer={shipper} onKey={setSigKey} />
          {view.documents.items.map((d) => (
            <Row
              key={d.doc_type}
              label={d.label}
              value={d.status}
              testID={`doc-${d.doc_type}`}
              onPress={
                d.status === "captured" || !sigKey
                  ? undefined
                  : () =>
                      void batchApi
                        .captureDoc(routeId, d.doc_type, {
                          media_key: docKey || undefined,
                          shipper_name: shipper,
                          shipper_signature_key: sigKey,
                          seal_no: seal || undefined,
                        })
                        .then(refresh, (e: Error) => toast.show("danger", "Not saved", e.message))
              }
            />
          ))}
        </Section>
      ) : null}
      <Row
        label={cardCopy("merchant_handover").button}
        value={s.merchantConfirmed ? "✓" : ""}
        onPress={() => setS({ ...s, merchantConfirmed: true })}
      />
      {blockers.map((b) => (
        <Text key={b} style={st.warn}>
          {blockMessage(b)}
        </Text>
      ))}
      <Button
        label="Confirm pickup"
        tone="primary"
        disabled={blockers.length > 0 || !photoKey}
        onPress={() =>
          void batchApi
            .confirmPickup(routeId, {
              count: s.counted,
              photo_key: photoKey,
              merchant_confirmed: true,
              scans: s.scanned,
              exceptions:
                s.countException && view
                  ? [{ kind: (s.counted ?? 0) < view.expected ? "short" : "extra" }]
                  : [],
            })
            .then(
              () => qc.invalidateQueries(),
              (e: Error) => toast.show("danger", "Pickup not confirmed", e.message)
            )
        }
      />
    </View>
  );
}

function DeliverBody({ routeId }: { routeId: string }) {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["batch-stops", routeId],
    queryFn: () => batchApi.stops(routeId),
    retry: false,
  });
  const [scanned, setScanned] = useState<Record<string, string[]>>({});
  const [disp, setDisp] = useState<Record<string, string>>({});
  if (q.error) return <Text style={st.warn}>{blockMessage("pickup_not_confirmed")}</Text>;
  if (!q.data) return <Text style={st.muted}>Loading…</Text>;
  const left = leftovers(q.data.stops);
  return (
    <View>
      {q.data.stops.map((stop) => {
        const got = scanned[stop.building_key] ?? [];
        const block = stop.parcels.length > 1 ? buildingBlockers(stop, got) : [];
        return (
          <Section
            key={stop.building_key}
            title={`${stop.stop_seq}. ${stop.address} (${stop.parcels.length})`}
          >
            {stop.parcels.map((p) => (
              <Row
                key={p.id}
                label={`${p.barcode}${p.unit ? ` · unit ${p.unit}` : ""}`}
                value={p.status === "delivered" ? "delivered" : got.includes(p.barcode) ? "✓" : ""}
                onPress={
                  p.status === "delivered"
                    ? undefined
                    : () => setScanned({ ...scanned, [stop.building_key]: [...got, p.barcode] })
                }
              />
            ))}
            {block.map((b) => (
              <Text key={b} style={st.warn}>
                {blockMessage(b)}
              </Text>
            ))}
            <Button
              label={
                stop.parcels.length > 1
                  ? cardCopy("building_scan").button
                  : cardCopy("scan_parcel").button
              }
              disabled={!got.length || block.length > 0}
              onPress={() =>
                void batchApi
                  .deliver(
                    routeId,
                    got,
                    stop.parcels.length > 1 ? { building_key: stop.building_key } : {}
                  )
                  .then(
                    () => qc.invalidateQueries({ queryKey: ["batch-stops", routeId] }),
                    (e: Error) => toast.show("danger", "Not delivered", e.message)
                  )
              }
            />
          </Section>
        );
      })}
      {left.length ? (
        <Section title="LEFTOVERS">
          {left.map((b) => (
            <Row
              key={b}
              label={b}
              value={disp[b] ?? "choose"}
              onPress={() =>
                setDisp({ ...disp, [b]: disp[b] === "return" ? "reattempt" : "return" })
              }
            />
          ))}
        </Section>
      ) : null}
      <Button
        label={cardCopy("leftover_disposition").button}
        disabled={left.some((b) => !disp[b])}
        onPress={() => void batchApi.close(routeId, disp).then(() => qc.invalidateQueries())}
      />
    </View>
  );
}

function HandoverBody({ routeId }: { routeId: string }) {
  const inc = useQuery({ queryKey: ["batch-incoming"], queryFn: () => batchApi.incoming() });
  const [to, setTo] = useState("");
  const [codes, setCodes] = useState("");
  const [outKey, setOutKey] = useState("");
  const [inKey, setInKey] = useState("");
  const [me, setMe] = useState("");
  const [sigKey, setSigKey] = useState("");
  const here = async () => {
    const fix = await readPosition(await loadLocation());
    if (!fix) throw new Error("location_needed");
    return fix.coords;
  };
  return (
    <Section title="DRIVER HANDOVER">
      <InputRow label="To driver ID" value={to} onChange={setTo} testID="ho-to" />
      <InputRow label="Parcel barcodes" value={codes} onChange={setCodes} testID="ho-codes" />
      <PhotoRow label="Handover photo" value={outKey} onKey={setOutKey} testID="ho-photo" />
      <Button
        label={cardCopy("handover_out").button}
        disabled={!to || !codes || !outKey}
        onPress={() =>
          void here()
            .then((c) =>
              batchApi.handover(routeId, {
                to_driver_id: to,
                codes: codes.split(/[\s,]+/).filter(Boolean),
                photo_key: outKey,
                lat: c.latitude,
                lng: c.longitude,
                place_kind: "meeting_point",
              })
            )
            .then(
              () => toast.show("success", "Handover started", ""),
              (e: Error) => toast.show("danger", "Handover failed", e.message)
            )
        }
      />
      {(inc.data?.items ?? []).length ? (
        <>
          <PhotoRow
            label="Received parcels photo"
            value={inKey}
            onKey={setInKey}
            testID="ho-in-photo"
          />
          <InputRow label="Your name" value={me} onChange={setMe} testID="ho-me" />
          <SignRow label="Your signature" signer={me} onKey={setSigKey} />
        </>
      ) : null}
      {(inc.data?.items ?? []).map((h) => (
        <Row
          key={h.id}
          label={`${h.parcels} parcels from ${h.from_driver_id}`}
          value={cardCopy("handover_in").button}
          onPress={
            inKey
              ? () =>
                  void here()
                    .then((c) =>
                      batchApi.accept(h.id, {
                        mode: "count",
                        count: h.parcels,
                        confirmed: true,
                        photo_key: inKey,
                        signature_key: sigKey || undefined,
                        lat: c.latitude,
                        lng: c.longitude,
                      })
                    )
                    .then(
                      () => inc.refetch(),
                      (e: Error) => toast.show("danger", "Not received", e.message)
                    )
              : undefined
          }
        />
      ))}
    </Section>
  );
}

const SAFETY = [
  ["unsafe_location", "Unsafe location"],
  ["suspicious_parcel", "Suspicious parcel"],
  ["theft_from_vehicle", "Theft from vehicle"],
] as const;

function SafetyBody({ routeId }: { routeId: string }) {
  const [code, setCode] = useState<string>("");
  const [note, setNote] = useState("");
  const [parcels, setParcels] = useState("");
  const [police, setPolice] = useState("");
  const [me, setMe] = useState("");
  const [photos, setPhotos] = useState<string[]>([]);
  const [sigKey, setSigKey] = useState("");
  const list = parcels.split(/[\s,]+/).filter(Boolean);
  return (
    <Section title="SAFETY REPORT">
      {SAFETY.map(([v, l]) => (
        <Row
          key={v}
          label={l}
          value={code === v ? "✓" : ""}
          onPress={() => setCode(v)}
          testID={`safety-${v}`}
        />
      ))}
      {code ? (
        <>
          <InputRow label="What happened" value={note} onChange={setNote} testID="safety-note" />
          <InputRow
            label="Parcel barcodes"
            value={parcels}
            onChange={setParcels}
            testID="safety-parcels"
          />
          {code === "theft_from_vehicle" ? (
            <InputRow label="Police report no." value={police} onChange={setPolice} />
          ) : null}
          <PhotoRow
            label={`Add photo (${photos.length})`}
            value=""
            onKey={(k) => setPhotos((p) => [...p, k])}
            testID="safety-photo"
          />
          <InputRow label="Your name" value={me} onChange={setMe} />
          <SignRow label="Your signature" signer={me} onKey={setSigKey} />
          <Button
            tone="primary"
            label="Send safety report"
            disabled={
              (code === "suspicious_parcel" && !photos.length) ||
              (code === "theft_from_vehicle" && !list.length)
            }
            onPress={() =>
              void safetyApi
                .report({
                  code,
                  route_id: routeId,
                  note: note || undefined,
                  parcels: list,
                  photo_keys: photos,
                  police_report_no: police || undefined,
                  signature_key: sigKey || undefined,
                })
                .then(
                  () => toast.show("success", "Reported", "Dispatch has been told. Stay safe."),
                  (e: Error) => toast.show("danger", "Not sent", e.message)
                )
            }
          />
        </>
      ) : null}
    </Section>
  );
}

const st = StyleSheet.create({
  wrap: { gap: space.md },
  h: { color: color.ink, fontWeight: "600" },
  muted: { color: color.inkMuted },
  warn: { color: color.danger },
});
