"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  type EditEntry,
  type Fetcher,
  type Instruction,
  type JobKind,
  type PickupDoc,
  PRIORITIES,
  STEPS,
  VISIBILITY,
  jobDocsClient,
  missingDocs,
  normaliseInstruction,
} from "@/lib/job-docs";

/** Pickup document checklist + instructions (with edit log) for one order or batch. */
export function JobDocsPanel({
  fetcher,
  base,
  kind,
  id,
  canPartner = false,
}: {
  fetcher: Fetcher;
  base: string;
  kind: JobKind;
  id: string;
  canPartner?: boolean;
}) {
  const api = useMemo(() => jobDocsClient(fetcher, base), [fetcher, base]);
  const [docs, setDocs] = useState<PickupDoc[]>([]);
  const [items, setItems] = useState<Instruction[]>([]);
  const [hist, setHist] = useState<Record<string, EditEntry[]>>({});
  const [err, setErr] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [priority, setPriority] = useState<string>("normal");
  const [vis, setVis] = useState<string[]>(["driver", "admin", "merchant"]);
  const [steps, setSteps] = useState<string[]>(["pickup", "delivery"]);
  const [business, setBusiness] = useState(false);
  const [partner, setPartner] = useState("");

  const load = useCallback(async () => {
    try {
      const [d, i] = await Promise.all([api.docs(kind, id), api.list(kind, id)]);
      setDocs(d.documents);
      setItems(i.items);
      setErr(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }, [api, kind, id]);
  useEffect(() => {
    void load();
  }, [load]);

  const toggle = (arr: string[], v: string, set: (x: string[]) => void) =>
    set(arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);

  async function add() {
    if (!text.trim()) return;
    try {
      await api.add(
        kind,
        id,
        normaliseInstruction({
          text,
          priority,
          visibility: vis,
          steps,
          business,
          ...(canPartner && partner ? { as_partner_id: partner } : {}),
        })
      );
      setText("");
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }
  async function remove(iid: string) {
    try {
      await api.edit(iid, { delete: true });
      await load();
    } catch (e) {
      setErr(String(e));
    }
  }
  async function showHistory(iid: string) {
    try {
      const h = await api.history(iid);
      setHist((x) => ({ ...x, [iid]: h.items }));
    } catch (e) {
      setErr(String(e));
    }
  }
  const missing = missingDocs(docs);

  return (
    <div className="space-y-4">
      {err && (
        <p role="alert" className="text-sm text-red-700">
          {err}
        </p>
      )}
      <section>
        <h3 className="font-semibold">Pickup documents</h3>
        {missing.length > 0 && (
          <p className="text-sm text-amber-700">Missing: {missing.join(", ")}</p>
        )}
        <table className="mt-2 w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500">
              <th>Document</th>
              <th>Status</th>
              <th>Shipper</th>
              <th>Scan / seal</th>
              <th>Captured</th>
            </tr>
          </thead>
          <tbody>
            {docs.length === 0 && (
              <tr>
                <td colSpan={5} className="text-slate-500">
                  No documents captured yet.
                </td>
              </tr>
            )}
            {docs.map((d) => (
              <tr key={d.id} className="border-t">
                <td>{d.doc_type}</td>
                <td>{d.status}</td>
                <td>{d.shipper_name ?? "—"}</td>
                <td>{d.scan_code ?? d.seal_no ?? (d.media_key ? "photo" : "—")}</td>
                <td>
                  {d.captured_at
                    ? new Date(d.captured_at).toLocaleString("en-CA", {
                        timeZone: "America/Toronto",
                      })
                    : (d.note ?? "—")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section>
        <h3 className="font-semibold">Instructions</h3>
        <ul className="mt-2 space-y-2">
          {items.map((i) => (
            <li key={i.id} className="rounded border p-2 text-sm">
              <div className="flex justify-between gap-2">
                <span>
                  <b>{i.priority}</b> · {i.text}
                </span>
                <span className="text-slate-500">
                  v{i.version} · {i.author_role} · {(i.steps ?? []).join("/")}
                  {i.business ? " · business" : ""}
                </span>
              </div>
              <div className="mt-1 flex gap-3">
                <button type="button" className="underline" onClick={() => void showHistory(i.id)}>
                  History
                </button>
                <button
                  type="button"
                  className="text-red-700 underline"
                  onClick={() => void remove(i.id)}
                >
                  Delete
                </button>
              </div>
              {hist[i.id] && (
                <ol className="mt-1 text-xs text-slate-600">
                  {hist[i.id].map((h, n) => (
                    <li key={n}>
                      {h.action} by {h.author_role} ({h.author_id}) at{" "}
                      {new Date(h.at).toLocaleString("en-CA", { timeZone: "America/Toronto" })}
                    </li>
                  ))}
                </ol>
              )}
            </li>
          ))}
        </ul>
        <div className="mt-3 space-y-2 rounded border p-3 text-sm">
          <textarea
            aria-label="Instruction text"
            className="w-full rounded border p-2"
            rows={2}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <div className="flex flex-wrap gap-3">
            <select
              aria-label="Priority"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
            >
              {PRIORITIES.map((p) => (
                <option key={p}>{p}</option>
              ))}
            </select>
            {VISIBILITY.map((v) => (
              <label key={v}>
                <input
                  type="checkbox"
                  checked={vis.includes(v)}
                  disabled={v === "driver" && business}
                  onChange={() => toggle(vis, v, setVis)}
                />{" "}
                {v}
              </label>
            ))}
            {STEPS.map((s) => (
              <label key={s}>
                <input
                  type="checkbox"
                  checked={steps.includes(s)}
                  onChange={() => toggle(steps, s, setSteps)}
                />{" "}
                {s}
              </label>
            ))}
            <label>
              <input
                type="checkbox"
                checked={business}
                onChange={(e) => setBusiness(e.target.checked)}
              />{" "}
              business (hidden from drivers)
            </label>
            {canPartner && (
              <input
                aria-label="On behalf of partner id"
                placeholder="partner id (optional)"
                className="rounded border px-1"
                value={partner}
                onChange={(e) => setPartner(e.target.value)}
              />
            )}
          </div>
          <button
            type="button"
            className="rounded bg-slate-900 px-3 py-1 text-white"
            onClick={() => void add()}
          >
            Add instruction
          </button>
        </div>
      </section>
    </div>
  );
}
