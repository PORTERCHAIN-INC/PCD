"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { FileText, Maximize2, X } from "lucide-react";
import { API_BASE } from "@/lib/api";

type Doc = {
  id: string;
  stop: "pickup" | "dropoff";
  kind_label: string;
  filename: string;
  content_type: string;
  note: string | null;
  required_at_stop: boolean;
  shown_at: string | null;
};

const CACHE = "pc-stop-docs-v1";

/** Fetch once, keep a copy for the warehouse (bad signal inside). Cleared when the job leaves the list. */
async function getBlob(id: string): Promise<Blob> {
  const url = `${API_BASE}/attachments/${id}/file`;
  try {
    const res = await fetch(url, { credentials: "include" });
    if (!res.ok) throw new Error(String(res.status));
    const blob = await res.blob();
    if ("caches" in window) {
      const c = await caches.open(CACHE);
      await c.put(url, new Response(blob, { headers: { "Content-Type": blob.type } }));
    }
    return blob;
  } catch (e) {
    if ("caches" in window) {
      const hit = await (await caches.open(CACHE)).match(url);
      if (hit) return hit.blob();
    }
    throw e;
  }
}

export function StopDocuments({ orderId, onChanged }: { orderId: string; onChanged?: () => void }) {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [showing, setShowing] = useState<{ doc: Doc; url: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const proofRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/orders/${orderId}/attachments`, {
        credentials: "include",
      });
      if (!res.ok) return;
      const body = (await res.json()) as { items: Doc[] };
      setDocs(body.items);
      body.items.forEach((d) => void getBlob(d.id).catch(() => undefined)); // pre-cache for offline
    } catch {
      /* offline: keep what we have */
    }
  }, [orderId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function open(doc: Doc) {
    setError(null);
    try {
      const blob = await getBlob(doc.id);
      setShowing({ doc, url: URL.createObjectURL(blob) });
    } catch {
      setError("Couldn't open the document. Check your connection and try again.");
    }
  }

  async function markShown(doc: Doc, proof?: File) {
    setBusy(true);
    setError(null);
    try {
      const fd = new FormData();
      if (proof) fd.set("proof", proof);
      const res = await fetch(`${API_BASE}/attachments/${doc.id}/shown`, {
        method: "POST",
        credentials: "include",
        body: fd,
      });
      if (!res.ok) throw new Error();
      setShowing(null);
      await load();
      onChanged?.();
    } catch {
      setError("Couldn't save. Try again when you have signal.");
    } finally {
      setBusy(false);
    }
  }

  if (docs.length === 0) return null;

  return (
    <section className="rounded-2xl border-2 border-amber-300 bg-amber-50 p-4">
      <h2 className="flex items-center gap-2 text-lg font-bold">
        <FileText className="h-5 w-5" /> Documents for this stop
      </h2>
      <ul className="mt-3 space-y-2">
        {docs.map((d) => (
          <li key={d.id} className="rounded-xl bg-white p-3">
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="font-semibold">{d.kind_label}</p>
                <p className="text-sm text-[var(--muted)]">
                  {d.filename} · {d.stop === "pickup" ? "Pickup" : "Drop-off"}
                </p>
                {d.note && <p className="mt-1 text-sm">Note: {d.note}</p>}
              </div>
              <button
                type="button"
                onClick={() => void open(d)}
                className="inline-flex items-center gap-1 rounded-xl bg-[var(--primary)] px-3 py-2 text-sm font-semibold text-white"
              >
                <Maximize2 className="h-4 w-4" /> Show to staff
              </button>
            </div>
            {d.required_at_stop && d.stop === "pickup" && (
              <p
                className={`mt-2 text-sm font-semibold ${d.shown_at ? "text-green-700" : "text-amber-800"}`}
              >
                {d.shown_at
                  ? "✓ Shown to warehouse staff"
                  : "Required: show document to warehouse staff before Picked up"}
              </p>
            )}
          </li>
        ))}
      </ul>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}

      {showing && (
        <div
          className="fixed inset-0 z-50 flex flex-col bg-white"
          role="dialog"
          aria-label="Show document to staff"
        >
          <div className="flex items-center justify-between border-b p-3">
            <p className="text-lg font-bold">{showing.doc.kind_label}</p>
            <button
              type="button"
              aria-label="Close"
              onClick={() => setShowing(null)}
              className="rounded-full p-2"
            >
              <X className="h-6 w-6" />
            </button>
          </div>
          <div className="flex-1 overflow-auto bg-white">
            {showing.doc.content_type === "application/pdf" ? (
              <iframe title={showing.doc.filename} src={showing.url} className="h-full w-full" />
            ) : (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={showing.url}
                alt={showing.doc.filename}
                className="mx-auto max-h-full w-full object-contain"
              />
            )}
          </div>
          <div className="grid grid-cols-2 gap-2 border-t p-3">
            <button
              type="button"
              disabled={busy}
              onClick={() => proofRef.current?.click()}
              className="rounded-xl border-2 border-[var(--primary)] px-3 py-4 text-base font-semibold"
            >
              Photo of signed copy
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => void markShown(showing.doc)}
              className="rounded-xl bg-green-600 px-3 py-4 text-base font-bold text-white"
            >
              {busy ? "Saving…" : "Shown to staff"}
            </button>
            <input
              ref={proofRef}
              type="file"
              accept="image/*"
              capture="environment"
              hidden
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void markShown(showing.doc, f);
              }}
            />
          </div>
        </div>
      )}
    </section>
  );
}
