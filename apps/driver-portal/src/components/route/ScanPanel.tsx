"use client";

import { useEffect, useState } from "react";
import { Check, Smartphone } from "lucide-react";
import { driverApi } from "@/lib/api";
import { actionErrorMessage } from "@/lib/jobs";
import { cn } from "@/lib/utils";

type Box = { code: string; label: string; done: boolean; missing?: boolean };

/**
 * Box checklist for the web portal. Label scanning is camera-only in the PorterChain
 * Driver app (iPhone + Android); the portal offers a typed label-code fallback and
 * shows recent scans. Every box must be scanned (or reported missing) before the
 * primary action unlocks.
 */
export function ScanPanel({
  title,
  boxes,
  onScan,
  onMissing,
}: {
  title: string;
  boxes: Box[];
  onScan: (code: string) => Promise<void>;
  onMissing?: (code: string) => void;
}) {
  const [manual, setManual] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const done = boxes.filter((b) => b.done).length; // a missing box is accounted for, never "scanned"

  const submit = async (raw: string) => {
    const code = raw.trim();
    if (!code) return;
    setMsg(null);
    try {
      await onScan(code);
      setManual("");
    } catch (e) {
      setMsg(e instanceof Error ? actionErrorMessage(e.message) : "Scan failed. Try again.");
    }
  };

  return (
    <div className="mt-5">
      <div className="flex items-baseline justify-between">
        <p className="text-sm font-semibold text-slate-800">{title}</p>
        <p className="text-2xl font-black tabular-nums text-[#0a1628]" aria-live="polite">
          {done}
          <span className="text-slate-400">/{boxes.length}</span>
        </p>
      </div>
      <p className="mt-3 flex items-center gap-2 rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
        <Smartphone className="h-5 w-5 shrink-0" aria-hidden />
        Scan labels with the PorterChain Driver app camera. Label won&apos;t scan? Type its code
        below.
      </p>
      <form
        className="mt-2 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void submit(manual);
        }}
      >
        <input
          value={manual}
          onChange={(e) => setManual(e.target.value)}
          aria-label="Label code"
          placeholder="Type the label code"
          autoCapitalize="characters"
          className="h-12 min-w-0 flex-1 rounded-xl border border-slate-300 px-3 text-base text-slate-900"
        />
        <button
          type="submit"
          className="h-12 rounded-xl bg-slate-100 px-4 text-sm font-bold text-slate-800"
        >
          Add
        </button>
      </form>
      {msg ? (
        <p role="alert" className="mt-2 text-sm font-medium text-red-700">
          {msg}
        </p>
      ) : null}
      <ul className="mt-3 space-y-2">
        {boxes.map((b) => (
          <li
            key={b.code}
            className={cn(
              "flex min-h-12 items-center gap-3 rounded-2xl border px-4",
              b.done
                ? "border-[#0a1628] bg-[#0a1628] text-white"
                : b.missing
                  ? "border-amber-300 bg-amber-50 text-amber-900"
                  : "border-slate-200 text-slate-900"
            )}
          >
            <span
              className={cn(
                "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2",
                b.done ? "border-[#38bdf8] bg-[#38bdf8]" : "border-slate-300"
              )}
            >
              {b.done ? <Check className="h-4 w-4 text-[#0a1628]" aria-hidden /> : null}
            </span>
            <span className="flex-1 text-base font-semibold">{b.label}</span>
            <span className={cn("font-mono text-xs", b.done ? "text-slate-300" : "text-slate-500")}>
              {b.code.slice(-6)}
            </span>
            {!b.done && !b.missing && onMissing ? (
              <button
                type="button"
                onClick={() => onMissing(b.code)}
                className="min-h-10 rounded-xl px-2 text-sm font-semibold text-amber-800"
              >
                Missing
              </button>
            ) : null}
            {b.missing ? <span className="text-sm font-semibold">Missing</span> : null}
          </li>
        ))}
      </ul>
      <ScanHistory />
    </div>
  );
}

const KIND: Record<string, string> = {
  lookup: "Looked up",
  pickup: "Pickup",
  delivery: "Delivery",
};
const RESULT: Record<string, string> = {
  ok: "OK",
  wrong_stop: "Wrong stop",
  not_yours: "Not your parcel",
  invalid_label_qr: "Unreadable label",
};

/** The driver's own recent scans (from the app or typed here), newest first. */
export function ScanHistory() {
  const [items, setItems] = useState<
    Awaited<ReturnType<typeof driverApi.scanHistory>>["items"] | null
  >(null);
  useEffect(() => {
    let live = true;
    driverApi
      .scanHistory(30)
      .then((r) => live && setItems(r.items))
      .catch(() => live && setItems([]));
    return () => {
      live = false;
    };
  }, []);
  if (!items || items.length === 0) return null;
  return (
    <details className="mt-4 rounded-2xl border border-slate-200 px-4 py-3">
      <summary className="cursor-pointer text-sm font-semibold text-slate-800">
        Recent scans ({items.length})
      </summary>
      <ul className="mt-2 divide-y divide-slate-100">
        {items.map((it, i) => (
          <li key={i} className="flex items-center justify-between py-2 text-sm">
            <span className="text-slate-700">{KIND[it.kind] ?? it.kind}</span>
            <span
              className={cn(
                "font-semibold",
                it.result === "ok" ? "text-emerald-700" : "text-amber-800"
              )}
            >
              {RESULT[it.result] ?? it.result}
            </span>
            <span className="tabular-nums text-slate-500">
              {it.at
                ? new Date(it.at).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
                : ""}
            </span>
          </li>
        ))}
      </ul>
    </details>
  );
}
