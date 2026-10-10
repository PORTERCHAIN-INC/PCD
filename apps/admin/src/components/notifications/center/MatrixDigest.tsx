"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { cn } from "@porterchain/ui/utils";
import { centerApi, fmtMs, fmtPct, type Persona } from "@/lib/notificationCenter";
import { PrimaryButton, QuietButton, Tone } from "./ui";

function useReady() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  return { getApiToken, ready: isLoaded && isSignedIn };
}

export function MatrixPanel() {
  const { getApiToken, ready } = useReady();
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["nc-matrix"],
    enabled: ready,
    queryFn: async () => centerApi.matrix(await getApiToken()),
  });
  const flip = async (event: string, persona: Persona, on: boolean) => {
    await centerApi.setCell(await getApiToken(), event, persona, !on);
    await qc.invalidateQueries({ queryKey: ["nc-matrix"] });
  };
  if (!data) return <p className="text-sm text-slate-600">Loading…</p>;
  return (
    <div>
      <p className="mb-3 text-sm text-slate-700">
        Platform switch per event and persona. Merchants still control their own receiver emails.
        Security and payment rows are locked on.
      </p>
      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
        <table className="w-full min-w-[40rem] text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-[11px] uppercase tracking-wide text-slate-600">
              <th scope="col" className="sticky left-0 bg-white px-4 py-3 font-semibold">
                Event
              </th>
              {data.personas.map((p) => (
                <th key={p} scope="col" className="px-3 py-3 text-center font-semibold">
                  {p}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data.rows.map((r) => (
              <tr key={r.event}>
                <th
                  scope="row"
                  className="sticky left-0 bg-white px-4 py-2 text-left font-mono text-xs font-medium text-slate-900"
                >
                  {r.event}
                </th>
                {data.personas.map((p) => {
                  const c = r.cells[p];
                  if (!c)
                    return (
                      <td
                        key={p}
                        className="px-3 py-2 text-center text-slate-300"
                        aria-label="not sent"
                      >
                        ·
                      </td>
                    );
                  return (
                    <td key={p} className="px-3 py-2 text-center">
                      <button
                        type="button"
                        role="switch"
                        aria-checked={c.on}
                        aria-label={`${r.event} to ${p}: ${c.on ? "on" : "off"}`}
                        disabled={c.locked}
                        onClick={() => flip(r.event, p, c.on)}
                        title={c.channels.join(" + ")}
                        className={cn(
                          "inline-flex h-6 w-11 items-center rounded-full p-0.5 transition disabled:cursor-not-allowed disabled:opacity-60",
                          c.on ? "bg-[#2563eb]" : "bg-slate-300"
                        )}
                      >
                        <span
                          className={cn(
                            "h-5 w-5 rounded-full bg-white shadow transition",
                            c.on ? "translate-x-5" : "translate-x-0"
                          )}
                        />
                      </button>
                      <span className="mt-0.5 block text-[10px] text-slate-600">
                        {c.channels.join("+")}
                      </span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function DigestPanel() {
  const { getApiToken, ready } = useReady();
  const qc = useQueryClient();
  const [busy, setBusy] = useState(false);
  const { data } = useQuery({
    queryKey: ["nc-digest"],
    enabled: ready,
    queryFn: async () => centerApi.digest(await getApiToken()),
  });
  const set = async (enabled: boolean) => {
    setBusy(true);
    try {
      await centerApi.setDigest(await getApiToken(), enabled, enabled);
      await qc.invalidateQueries({ queryKey: ["nc-digest"] });
    } finally {
      setBusy(false);
    }
  };
  if (!data) return <p className="text-sm text-slate-600">Loading…</p>;
  const p = data.preview;
  const s = data.settings;
  const nums: [string, string][] = [
    ["Delivered", String(p.delivered ?? 0)],
    ["Failed", String(p.failed ?? 0)],
    ["Success", fmtPct(p.success_pct as number | null)],
    ["Exceptions", String(p.exceptions_opened ?? 0)],
    ["Email p95", fmtMs(p.email_p95_ms as number | null)],
    ["Dead letters", String(p.dead_letters ?? 0)],
  ];
  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-slate-900">Daily ops summary</h2>
            <p className="text-sm text-slate-700">
              One email to ops at {s.send_hour}:00 Toronto with yesterday&apos;s numbers. Replaces
              per-event noise.
            </p>
          </div>
          {s.enabled ? (
            <Tone tone="ok">On · approved by {s.approved_by}</Tone>
          ) : (
            <Tone tone="idle">Off</Tone>
          )}
        </div>
        <div className="mt-4">
          {s.enabled ? (
            <QuietButton disabled={busy} onClick={() => set(false)}>
              Turn off
            </QuietButton>
          ) : (
            <PrimaryButton disabled={busy} onClick={() => set(true)}>
              Approve and turn on
            </PrimaryButton>
          )}
          {s.last_sent_date ? (
            <span className="ml-3 text-sm text-slate-600">Last sent {s.last_sent_date}</span>
          ) : null}
        </div>
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-600">
          Preview · {String(p.date)}
        </p>
        <dl className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-3">
          {nums.map(([k, v]) => (
            <div key={k}>
              <dd className="text-2xl font-extrabold tabular-nums text-slate-900">{v}</dd>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-600">{k}</dt>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}
