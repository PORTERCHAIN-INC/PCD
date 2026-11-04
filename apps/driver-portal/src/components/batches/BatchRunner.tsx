"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  adviceText,
  blockMessage,
  cardCopy,
  handlingLabels,
  type ScanAdvice,
} from "@porterchain/driver-flows";
import { batchApi, safetyApi } from "@/lib/api";
import {
  buildingBlockers,
  leftovers,
  pickupBlockers,
  type Instruction,
  type PickupState,
} from "@/lib/batches";
import { currentPosition } from "@/lib/dispatch-route";
import { PhotoField, SignaturePad } from "@/components/media/SignaturePad";

function Notes({
  items,
  acked,
  onAck,
}: {
  items: Instruction[];
  acked: string[];
  onAck: (id: string) => void;
}) {
  if (!items.length) return null;
  return (
    <ul className="space-y-2" aria-label="Instructions">
      {items.map((i) => (
        <li
          key={i.id}
          className={`rounded border p-2 text-sm ${i.priority === "must_read" ? "border-amber-500" : ""}`}
        >
          <span className="font-medium">
            {i.priority === "must_read"
              ? "Must read: "
              : i.priority === "high"
                ? "Important: "
                : ""}
          </span>
          {i.text}
          {i.priority === "must_read" && !i.acknowledged && !acked.includes(i.id) && (
            <button className="ml-2 underline" onClick={() => onAck(i.id)}>
              {cardCopy("instructions").button}
            </button>
          )}
        </li>
      ))}
    </ul>
  );
}

function Pickup({ routeId }: { routeId: string }) {
  const qc = useQueryClient();
  const v = useQuery({
    queryKey: ["batch-pickup", routeId],
    queryFn: () => batchApi.pickup(routeId),
  });
  const [s, setS] = useState<PickupState>({ scanned: [], acked: [] });
  const [code, setCode] = useState("");
  const [advice, setAdvice] = useState<ScanAdvice | null>(null);
  const [doc, setDoc] = useState({
    shipper_name: "",
    scan_code: "",
    seal_no: "",
    sigKey: "",
    mediaKey: "",
  });
  const [photoKey, setPhotoKey] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const refresh = () => qc.invalidateQueries({ queryKey: ["batch-pickup", routeId] });
  const confirm = useMutation({
    mutationFn: async () => {
      const pos = await currentPosition().catch(() => null);
      return batchApi.confirmPickup(routeId, {
        count: s.counted,
        photo_key: photoKey,
        merchant_confirmed: s.merchantConfirmed,
        scans: s.scanned,
        lat: pos?.lat,
        lng: pos?.lng,
        exceptions:
          s.countException && s.counted != null && v.data
            ? [{ kind: s.counted < v.data.expected ? "short" : "extra" }]
            : [],
      });
    },
    onSuccess: refresh,
    onError: (e: Error) => setErr(e.message),
  });
  if (!v.data) return <p>{v.error ? String(v.error) : "Loading…"}</p>;
  const view = v.data;
  const blockers = pickupBlockers(view, s);
  const onScan = async () => {
    const a = await batchApi.scan(routeId, code, "pickup", s.scanned);
    setAdvice(a);
    const bc = a.barcode;
    if (bc && !s.scanned.includes(bc)) setS({ ...s, scanned: [...s.scanned, bc] });
    setCode("");
  };
  return (
    <section className="space-y-3">
      {view.documents.reminders.map((r) => (
        <p key={r} className="text-sm text-amber-700">
          {r}
        </p>
      ))}
      <Notes
        items={view.instructions.items}
        acked={s.acked}
        onAck={async (id) => {
          await batchApi.ack(id);
          setS({ ...s, acked: [...s.acked, id] });
        }}
      />
      <h2 className="font-semibold">
        {cardCopy("batch_parcel_list").title} ({view.expected})
      </h2>
      <ol className="text-sm">
        {view.parcels.map((p) => (
          <li key={p.id}>
            #{p.load_position} {p.barcode} · {p.address}
            {p.unit ? ` u${p.unit}` : ""} {handlingLabels(p.handling).join(", ")}
            {view.spot_sample.includes(p.barcode) && " · spot check"}
            {p.scan_required && " · scan"}
            {s.scanned.includes(p.barcode) && " ✓"}
          </li>
        ))}
      </ol>
      <div className="flex gap-2">
        <input
          aria-label="Scan code"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          className="border px-2"
        />
        <button onClick={onScan} disabled={!code}>
          Scan
        </button>
      </div>
      {advice && <p role="status">{adviceText(advice)}</p>}
      <label>
        Count{" "}
        <input
          type="number"
          aria-label="Count"
          onChange={(e) => setS({ ...s, counted: Number(e.target.value) })}
        />
      </label>
      <PhotoField
        label={cardCopy("count_photo").button}
        onSaved={(k) => {
          setPhotoKey(k ?? "");
          setS({ ...s, photo: !!k });
        }}
      />
      <label>
        <input type="checkbox" onChange={(e) => setS({ ...s, countException: e.target.checked })} />{" "}
        {cardCopy("count_exception").title}
      </label>
      {view.documents.items.length > 0 && (
        <div className="space-y-1">
          <h3 className="font-semibold">{cardCopy("pickup_docs").title}</h3>
          <input
            placeholder="Document scan / number"
            value={doc.scan_code}
            onChange={(e) => setDoc({ ...doc, scan_code: e.target.value })}
          />
          <input
            placeholder="Seal number"
            value={doc.seal_no}
            onChange={(e) => setDoc({ ...doc, seal_no: e.target.value })}
          />
          <PhotoField
            label="Document photo"
            onSaved={(k) => setDoc((d) => ({ ...d, mediaKey: k ?? "" }))}
          />
          <SignaturePad
            label="Shipper signature"
            signerLabel="Shipper name"
            onSaved={(k, name) => setDoc((d) => ({ ...d, sigKey: k ?? "", shipper_name: name }))}
          />
          {view.documents.items.map((d) => (
            <div key={d.doc_type} className="text-sm">
              {d.label}: {d.status}
              {d.status !== "captured" && (
                <>
                  <button
                    className="ml-2 underline"
                    disabled={!doc.shipper_name || !doc.sigKey}
                    onClick={() =>
                      batchApi
                        .captureDoc(routeId, d.doc_type, {
                          scan_code: doc.scan_code || undefined,
                          media_key: doc.mediaKey || undefined,
                          seal_no: doc.seal_no || undefined,
                          shipper_name: doc.shipper_name,
                          shipper_signature_key: doc.sigKey,
                        })
                        .then(refresh, (e: Error) => setErr(e.message))
                    }
                  >
                    Capture
                  </button>
                  <button
                    className="ml-2 underline"
                    onClick={() => {
                      const r = window.prompt("Why is it missing?");
                      if (r) batchApi.docMissing(routeId, d.doc_type, r).then(refresh);
                    }}
                  >
                    Missing
                  </button>
                </>
              )}
            </div>
          ))}
        </div>
      )}
      <label>
        <input
          type="checkbox"
          onChange={(e) => setS({ ...s, merchantConfirmed: e.target.checked })}
        />{" "}
        {cardCopy("merchant_handover").button}
      </label>
      <ul className="text-sm text-red-700">
        {blockers.map((b) => (
          <li key={b}>{blockMessage(b)}</li>
        ))}
      </ul>
      {err && <p className="text-red-700">{err}</p>}
      <button
        disabled={blockers.length > 0 || !photoKey || confirm.isPending}
        onClick={() => confirm.mutate()}
      >
        Confirm pickup
      </button>
    </section>
  );
}

function Deliver({ routeId }: { routeId: string }) {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["batch-stops", routeId],
    queryFn: () => batchApi.stops(routeId),
    retry: false,
  });
  const [scanned, setScanned] = useState<Record<string, string[]>>({});
  const [disp, setDisp] = useState<Record<string, string>>({});
  if (q.error) return <p>{blockMessage("pickup_not_confirmed")}</p>;
  if (!q.data) return <p>Loading…</p>;
  const left = leftovers(q.data.stops);
  return (
    <section className="space-y-3">
      {q.data.stops.map((st) => {
        const got = scanned[st.building_key] ?? [];
        const block = st.parcels.length > 1 ? buildingBlockers(st, got) : [];
        return (
          <div key={st.building_key} className="rounded border p-2">
            <p className="font-medium">
              {st.stop_seq}. {st.address} ({st.parcels.length}){" "}
              {handlingLabels(st.handling).join(", ")}
            </p>
            {st.parcels.map((p) => (
              <label key={p.id} className="block text-sm">
                <input
                  type="checkbox"
                  disabled={p.status === "delivered"}
                  checked={got.includes(p.barcode) || p.status === "delivered"}
                  onChange={(e) =>
                    setScanned({
                      ...scanned,
                      [st.building_key]: e.target.checked
                        ? [...got, p.barcode]
                        : got.filter((x) => x !== p.barcode),
                    })
                  }
                />
                {p.barcode}
                {p.unit ? ` unit ${p.unit}` : ""} {p.recipient ?? ""}
              </label>
            ))}
            {block.map((b) => (
              <p key={b} className="text-sm text-red-700">
                {blockMessage(b)}
              </p>
            ))}
            <button
              disabled={!got.length || block.length > 0}
              onClick={() =>
                batchApi
                  .deliver(
                    routeId,
                    got,
                    st.parcels.length > 1 ? { building_key: st.building_key } : {}
                  )
                  .then(
                    () => qc.invalidateQueries({ queryKey: ["batch-stops", routeId] }),
                    (e: Error) => alert(e.message)
                  )
              }
            >
              {st.parcels.length > 1
                ? cardCopy("building_scan").button
                : cardCopy("scan_parcel").button}
            </button>
          </div>
        );
      })}
      {left.length > 0 && (
        <div>
          <h3 className="font-semibold">{cardCopy("leftover_disposition").title}</h3>
          {left.map((b) => (
            <label key={b} className="block text-sm">
              {b}
              <select
                aria-label={`disposition ${b}`}
                value={disp[b] ?? ""}
                onChange={(e) => setDisp({ ...disp, [b]: e.target.value })}
              >
                <option value="">—</option>
                <option value="return">Return to depot</option>
                <option value="reattempt">Re-attempt</option>
              </select>
            </label>
          ))}
        </div>
      )}
      <button
        disabled={left.some((b) => !disp[b])}
        onClick={() => batchApi.close(routeId, disp).then(() => qc.invalidateQueries())}
      >
        {cardCopy("leftover_disposition").button}
      </button>
    </section>
  );
}

function Handover({ routeId }: { routeId: string }) {
  const inc = useQuery({ queryKey: ["batch-incoming"], queryFn: () => batchApi.incoming() });
  const [to, setTo] = useState("");
  const [codes, setCodes] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [outKey, setOutKey] = useState("");
  const [inKey, setInKey] = useState("");
  const [sigKey, setSigKey] = useState("");
  const give = async () => {
    const pos = await currentPosition();
    await batchApi
      .handover(routeId, {
        to_driver_id: to,
        codes: codes.split(/[\s,]+/).filter(Boolean),
        photo_key: outKey,
        lat: pos?.lat ?? NaN,
        lng: pos?.lng ?? NaN,
        place_kind: "meeting_point",
      })
      .then(
        () => setMsg("Handover started"),
        (e: Error) => setMsg(e.message)
      );
  };
  const accept = async (id: string, n: number) => {
    const pos = await currentPosition();
    await batchApi
      .accept(id, {
        mode: "count",
        count: n,
        confirmed: true,
        photo_key: inKey,
        signature_key: sigKey || undefined,
        lat: pos?.lat ?? NaN,
        lng: pos?.lng ?? NaN,
      })
      .then(
        () => {
          setMsg("Received");
          inc.refetch();
        },
        (e: Error) => setMsg(e.message)
      );
  };
  return (
    <section className="space-y-2">
      <h3 className="font-semibold">{cardCopy("handover_out").title}</h3>
      <input placeholder="Driver ID" value={to} onChange={(e) => setTo(e.target.value)} />
      <textarea
        placeholder="Parcel barcodes"
        value={codes}
        onChange={(e) => setCodes(e.target.value)}
      />
      <PhotoField label="Handover photo" onSaved={(k) => setOutKey(k ?? "")} />
      <button disabled={!to || !codes || !outKey} onClick={give}>
        {cardCopy("handover_out").button}
      </button>
      <h3 className="font-semibold">{cardCopy("handover_in").title}</h3>
      <PhotoField label="Received parcels photo" onSaved={(k) => setInKey(k ?? "")} />
      <SignaturePad
        label="Receiving driver signature"
        signerLabel="Your name"
        onSaved={(k) => setSigKey(k ?? "")}
      />
      {(inc.data?.items ?? []).map((h) => (
        <p key={h.id}>
          {h.parcels} parcels from {h.from_driver_id}
          <button
            className="ml-2 underline"
            disabled={!inKey}
            onClick={() => accept(h.id, h.parcels)}
          >
            {cardCopy("handover_in").button}
          </button>
        </p>
      ))}
      {msg && <p role="status">{msg}</p>}
    </section>
  );
}

const SAFETY_CODES = [
  ["suspicious_parcel", "Suspicious parcel"],
  ["unsafe_location", "Unsafe location"],
  ["theft_from_vehicle", "Theft from vehicle"],
] as const;

function Safety({ routeId }: { routeId: string }) {
  const [code, setCode] = useState<string>("unsafe_location");
  const [note, setNote] = useState("");
  const [parcels, setParcels] = useState("");
  const [police, setPolice] = useState("");
  const [photos, setPhotos] = useState<string[]>([]);
  const [sigKey, setSigKey] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const send = () =>
    safetyApi
      .report({
        code,
        route_id: routeId,
        note: note || undefined,
        parcels: parcels.split(/[\s,]+/).filter(Boolean),
        photo_keys: photos,
        police_report_no: police || undefined,
        signature_key: sigKey || undefined,
      })
      .then(
        () => setMsg("Reported. Stay safe; dispatch has been told."),
        (e: Error) => setMsg(e.message)
      );
  return (
    <section className="space-y-2">
      <select aria-label="Safety issue" value={code} onChange={(e) => setCode(e.target.value)}>
        {SAFETY_CODES.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
      <textarea
        placeholder="What happened"
        value={note}
        onChange={(e) => setNote(e.target.value)}
      />
      <textarea
        placeholder="Parcel barcodes (if any)"
        value={parcels}
        onChange={(e) => setParcels(e.target.value)}
      />
      {code === "theft_from_vehicle" && (
        <input
          placeholder="Police report number"
          value={police}
          onChange={(e) => setPolice(e.target.value)}
        />
      )}
      <PhotoField label="Add photo" onSaved={(k) => k && setPhotos((p) => [...p, k])} />
      {photos.length > 0 && <p className="text-sm">{photos.length} photo(s) attached</p>}
      <SignaturePad
        label="Your signature"
        signerLabel="Your name"
        onSaved={(k) => setSigKey(k ?? "")}
      />
      <button
        disabled={
          (code === "suspicious_parcel" && !photos.length) ||
          (code === "theft_from_vehicle" && !parcels.trim())
        }
        onClick={send}
      >
        Send safety report
      </button>
      {msg && <p role="status">{msg}</p>}
    </section>
  );
}

export default function BatchRunner() {
  const routes = useQuery({ queryKey: ["batch-routes"], queryFn: () => batchApi.routes() });
  const [sel, setSel] = useState<string | null>(null);
  const [tab, setTab] = useState<"pickup" | "deliver" | "handover" | "safety">("pickup");
  const items = routes.data?.items ?? [];
  const active = items.find((r) => r.id === sel) ?? items[0];
  return (
    <main className="space-y-4 p-4">
      <h1 className="text-xl font-semibold">Batches</h1>
      {!items.length && <p>No batch routes assigned.</p>}
      {items.length > 1 && (
        <select aria-label="Route" value={active?.id} onChange={(e) => setSel(e.target.value)}>
          {items.map((r) => (
            <option key={r.id} value={r.id}>
              Route {r.route_no} · wave {r.wave} · {r.status}
            </option>
          ))}
        </select>
      )}
      {active && (
        <>
          <nav
            aria-label="Route steps"
            className="flex gap-1 rounded-2xl border border-primary/10 bg-white p-1"
          >
            {(["pickup", "deliver", "handover", "safety"] as const).map((t) => (
              <button
                key={t}
                type="button"
                aria-pressed={tab === t}
                onClick={() => setTab(t)}
                className={`min-h-11 flex-1 rounded-xl px-3 text-sm font-semibold capitalize transition ${tab === t ? "bg-primary text-white shadow-sm" : "text-primary hover:bg-primary/5"}`}
              >
                {t}
              </button>
            ))}
          </nav>
          {active.status === "awaiting_handover" && tab === "pickup" && (
            <p>{cardCopy("handover_in").title}</p>
          )}
          {tab === "pickup" && active.status === "planned" && <Pickup routeId={active.id} />}
          {tab === "deliver" && <Deliver routeId={active.id} />}
          {tab === "handover" && <Handover routeId={active.id} />}
          {tab === "safety" && <Safety routeId={active.id} />}
        </>
      )}
    </main>
  );
}
