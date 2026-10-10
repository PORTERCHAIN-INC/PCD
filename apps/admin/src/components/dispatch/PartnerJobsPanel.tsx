"use client";

import { useState } from "react";
import { MoreHorizontal } from "lucide-react";
import { useApiData } from "@/hooks/useApiData";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import {
  LEG_STATUS_LABEL,
  dispatch,
  money,
  type LegStatus,
  type PartnerEmailDraft,
  type PartnerLeg,
} from "@/lib/dispatch";

const FLOW: LegStatus[] = ["planned", "requested", "accepted", "picked_up", "delivered"];
const MODE: Record<PartnerLeg["mode"], string> = { warehouse: "Warehouse", ftl: "FTL", ltl: "LTL", "3pl": "3PL", local: "Van" };
const NEXT_LABEL: Partial<Record<LegStatus, string>> = {
  requested: "Mark requested",
  accepted: "Mark accepted",
  picked_up: "Mark picked up",
  delivered: "Mark delivered",
};

/** Partner (3PL / LTL / FTL / warehouse) legs: job sheet + email draft, manual status. Nothing is sent. */
export function PartnerJobsPanel({ tick }: { tick: number }) {
  const { getApiToken } = useAdminAuth();
  const { data, loading, refetch } = useApiData((t) => dispatch.partnerLegs(t), [tick], { key: "dispatch-partner-legs" });
  const [menu, setMenu] = useState<string | null>(null);
  const [draft, setDraft] = useState<PartnerEmailDraft | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const items = data?.items ?? [];
  const counts = FLOW.map((s) => [s, items.filter((i) => i.status === s).length] as const);

  const run = async (fn: (t: string) => Promise<unknown>) => {
    setMsg(null);
    try {
      await fn(await getApiToken());
      await refetch();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Failed");
    }
  };

  const openPdf = async (leg: PartnerLeg) => {
    setMenu(null);
    const t = await getApiToken();
    const res = await fetch(`/api/porterchain${dispatch.partnerLegPdfPath(leg.id)}`, {
      credentials: "include",
      headers: { Authorization: `Bearer ${t}` },
    });
    if (!res.ok) return setMsg("Job sheet failed");
    window.open(URL.createObjectURL(await res.blob()), "_blank", "noopener");
  };

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-4" data-testid="dispatch-partner-jobs">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-primary">Partner jobs</h2>
          <p className="text-xs text-muted">Job sheet and email are drafts — you send them. Update status by hand.</p>
        </div>
        <dl className="flex gap-4" aria-label="Partner jobs by status">
          {counts.map(([s, n]) => (
            <div key={s} className="text-right">
              <dt className="text-[11px] uppercase tracking-wider text-muted">{LEG_STATUS_LABEL[s]}</dt>
              <dd className="text-xl font-black tabular-nums text-primary">{n}</dd>
            </div>
          ))}
        </dl>
      </header>

      {loading && !data ? (
        <div className="mt-3 space-y-2" aria-busy="true">
          {[0, 1].map((i) => <div key={i} className="h-12 animate-pulse rounded-xl bg-primary/5" />)}
        </div>
      ) : items.length === 0 ? (
        <p className="mt-4 text-sm text-muted">No partner legs. Out-of-area orders get them from “Plan legs” on the order.</p>
      ) : (
        <ul className="mt-3 divide-y divide-primary/5">
          {items.map((leg) => {
            const next = leg.next.find((s) => s !== "cancelled");
            return (
              <li key={leg.id} className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-2 py-3 text-sm sm:flex">
                <span className="rounded-full bg-primary/5 px-2 py-0.5 text-xs font-semibold text-primary">{MODE[leg.mode]}</span>
                <span className="min-w-0 sm:flex-1">
                  <span className="block truncate font-semibold text-primary">
                    {leg.order_number ?? leg.order_id.slice(0, 8)} · {leg.partner_name ?? "No partner"}
                  </span>
                  <span className="block truncate text-xs text-muted">
                    {leg.from_label ?? "—"} → {leg.to_label ?? "—"}
                    {leg.est_cost_cents ? ` · ${money(leg.est_cost_cents)}` : ""}
                  </span>
                </span>
                <span
                  className={
                    "rounded-full px-2 py-0.5 text-xs font-semibold " +
                    (leg.status === "delivered"
                      ? "bg-emerald-100 text-emerald-900"
                      : leg.status === "cancelled"
                        ? "bg-slate-100 text-slate-700"
                        : "bg-sky-100 text-sky-900")
                  }
                >
                  {LEG_STATUS_LABEL[leg.status]}
                </span>
                {next ? (
                  <button
                    type="button"
                    onClick={() => run((t) => dispatch.setPartnerLegStatus(t, leg.id, next))}
                    className="col-span-2 min-h-11 rounded-xl px-3 text-sm font-semibold text-white"
                    style={{ backgroundColor: "var(--primary)" }}
                  >
                    {NEXT_LABEL[next] ?? next}
                  </button>
                ) : null}
                <div className={next ? "relative" : "relative col-start-3"}>
                  <button
                    type="button"
                    aria-label={`More for ${leg.order_number ?? "leg"}`}
                    aria-expanded={menu === leg.id}
                    onClick={() => setMenu(menu === leg.id ? null : leg.id)}
                    className="flex h-11 w-11 items-center justify-center rounded-xl border border-primary/15 text-primary"
                  >
                    <MoreHorizontal className="h-4 w-4" aria-hidden />
                  </button>
                  {menu === leg.id && (
                    <div role="menu" className="absolute right-0 z-20 mt-1 w-52 rounded-xl border border-primary/10 bg-white p-1 shadow-xl">
                      <button role="menuitem" type="button" className="block w-full rounded-lg px-3 py-2 text-left text-sm text-primary hover:bg-primary/5" onClick={() => void openPdf(leg)}>
                        Job sheet (PDF)
                      </button>
                      <button
                        role="menuitem"
                        type="button"
                        className="block w-full rounded-lg px-3 py-2 text-left text-sm text-primary hover:bg-primary/5"
                        onClick={async () => {
                          setMenu(null);
                          try {
                            setDraft(await dispatch.draftPartnerLeg(await getApiToken(), leg.id));
                          } catch (e) {
                            setMsg(e instanceof Error ? e.message : "Draft failed");
                          }
                        }}
                      >
                        Email draft
                      </button>
                      {leg.next.includes("cancelled") && (
                        <button
                          role="menuitem"
                          type="button"
                          className="block w-full rounded-lg px-3 py-2 text-left text-sm text-red-700 hover:bg-red-50"
                          onClick={() => {
                            setMenu(null);
                            if (window.confirm("Cancel this partner leg?")) void run((t) => dispatch.setPartnerLegStatus(t, leg.id, "cancelled"));
                          }}
                        >
                          Cancel leg
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
      {msg && <p role="alert" className="mt-2 text-sm text-red-700">{msg}</p>}

      {draft && (
        <div role="dialog" aria-modal="true" aria-label="Partner email draft" className="fixed inset-0 z-50 flex items-end justify-center bg-primary/40 p-3 sm:items-center">
          <div className="w-full max-w-lg rounded-2xl bg-white p-5 shadow-2xl">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted">Draft · not sent</p>
            <p className="mt-2 text-sm text-primary"><span className="text-muted">To </span>{draft.to ?? "add the partner's ops email"}</p>
            <p className="mt-1 text-sm font-semibold text-primary">{draft.subject}</p>
            <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap rounded-xl bg-primary/[0.03] p-3 text-xs text-primary">{draft.body}</pre>
            <p className="mt-2 text-xs text-muted">Attach {draft.attachment} from “Job sheet (PDF)”, then send from your mail.</p>
            <div className="mt-4 flex gap-2">
              <button
                type="button"
                className="min-h-11 flex-1 rounded-xl text-sm font-semibold text-white"
                style={{ backgroundColor: "var(--primary)" }}
                onClick={() => void navigator.clipboard?.writeText(`To: ${draft.to ?? ""}\nSubject: ${draft.subject}\n\n${draft.body}`)}
              >
                Copy email
              </button>
              <button type="button" className="min-h-11 rounded-xl px-4 text-sm text-primary" onClick={() => setDraft(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
