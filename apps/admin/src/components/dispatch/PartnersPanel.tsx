"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { useApiData } from "@/hooks/useApiData";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { dispatch, money, type LogisticsPartner } from "@/lib/dispatch";

const IN = "w-full min-w-0 rounded-lg border border-primary/15 bg-white px-2 py-1.5 text-sm text-primary";
const KIND_LABEL: Record<LogisticsPartner["kind"], string> = {
  warehouse: "Warehouse",
  ftl: "FTL",
  ltl: "LTL",
  "3pl": "3PL",
};

const EMPTY: LogisticsPartner = {
  name: "",
  kind: "warehouse",
  lat: null,
  lng: null,
  fsa_coverage: [],
  rate_per_kg_cents: 0,
  min_charge_cents: 0,
  transit_days: 1,
  cutoff_local: null,
  contact_email: null,
  active: true,
};

export function PartnersPanel({ tick }: { tick: number }) {
  const { getApiToken } = useAdminAuth();
  const { data, refetch } = useApiData((t) => dispatch.partners(t), [tick], { key: "dispatch-partners" });
  const [draft, setDraft] = useState<LogisticsPartner | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const items = data?.items ?? [];

  const save = async () => {
    if (!draft) return;
    setMsg("Saving…");
    try {
      await dispatch.savePartner(await getApiToken(), draft);
      setDraft(null);
      setMsg(null);
      await refetch();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Save failed");
    }
  };

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-4" data-testid="dispatch-partners">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-primary">Partners</h2>
          <p className="text-xs text-muted">Warehouses, FTL/LTL linehaul and 3PL final mile. Used for out-of-area legs.</p>
        </div>
        <button
          type="button"
          onClick={() => setDraft({ ...EMPTY })}
          className="inline-flex min-h-10 items-center gap-1.5 rounded-xl border border-primary/15 px-3 text-sm font-medium text-primary"
        >
          <Plus className="h-4 w-4" /> Add partner
        </button>
      </header>

      {items.length === 0 && !draft && (
        <p className="mt-3 text-sm text-muted">No partners yet — every order runs as a local van leg.</p>
      )}
      {items.length > 0 && (
        <ul className="mt-3 divide-y divide-primary/5">
          {items.map((p) => (
            <li key={p.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2 text-sm">
              <span className="rounded-full bg-primary/5 px-2 py-0.5 text-xs font-semibold text-primary">
                {KIND_LABEL[p.kind]}
              </span>
              <span className="min-w-0 flex-1 truncate font-medium text-primary">{p.name}</span>
              <span className="text-xs text-muted">
                {p.kind === "warehouse"
                  ? `${p.lat?.toFixed(3)}, ${p.lng?.toFixed(3)}`
                  : `${money(p.rate_per_kg_cents)}/kg · min ${money(p.min_charge_cents)}`}
                {p.fsa_coverage.length ? ` · ${p.fsa_coverage.join(" ")}` : ""}
                {p.active ? "" : " · off"}
              </span>
              <button type="button" className="text-xs font-medium text-secondary" onClick={() => setDraft({ ...p })}>
                Edit
              </button>
            </li>
          ))}
        </ul>
      )}

      {draft && (
        <div className="mt-3 grid gap-3 rounded-xl bg-primary/[0.03] p-3 sm:grid-cols-4">
          <label className="text-xs text-muted sm:col-span-2">
            Name
            <input className={IN} value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
          </label>
          <label className="text-xs text-muted">
            Type
            <select
              className={IN}
              value={draft.kind}
              onChange={(e) => setDraft({ ...draft, kind: e.target.value as LogisticsPartner["kind"] })}
            >
              {Object.entries(KIND_LABEL).map(([k, l]) => (
                <option key={k} value={k}>
                  {l}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-end gap-2 text-xs text-muted">
            <input
              type="checkbox"
              checked={draft.active}
              onChange={(e) => setDraft({ ...draft, active: e.target.checked })}
            />
            Active
          </label>
          {draft.kind === "warehouse" ? (
            <>
              <label className="text-xs text-muted">
                Lat
                <input
                  className={IN}
                  type="number"
                  step="0.0001"
                  value={draft.lat ?? ""}
                  onChange={(e) => setDraft({ ...draft, lat: e.target.value === "" ? null : Number(e.target.value) })}
                />
              </label>
              <label className="text-xs text-muted">
                Lng
                <input
                  className={IN}
                  type="number"
                  step="0.0001"
                  value={draft.lng ?? ""}
                  onChange={(e) => setDraft({ ...draft, lng: e.target.value === "" ? null : Number(e.target.value) })}
                />
              </label>
            </>
          ) : (
            <>
              <label className="text-xs text-muted">
                Rate $/kg
                <input
                  className={IN}
                  type="number"
                  step="0.01"
                  value={draft.rate_per_kg_cents / 100}
                  onChange={(e) => setDraft({ ...draft, rate_per_kg_cents: Math.round(Number(e.target.value) * 100) })}
                />
              </label>
              <label className="text-xs text-muted">
                Min charge $
                <input
                  className={IN}
                  type="number"
                  value={draft.min_charge_cents / 100}
                  onChange={(e) => setDraft({ ...draft, min_charge_cents: Math.round(Number(e.target.value) * 100) })}
                />
              </label>
            </>
          )}
          <label className="text-xs text-muted sm:col-span-2">
            Ops email (for job requests)
            <input
              className={IN}
              type="email"
              placeholder="dispatch@partner.ca"
              value={draft.contact_email ?? ""}
              onChange={(e) => setDraft({ ...draft, contact_email: e.target.value || null })}
            />
          </label>
          <label className="text-xs text-muted sm:col-span-2">
            FSA coverage (prefixes)
            <input
              className={IN}
              placeholder="K1 K2 H3"
              value={draft.fsa_coverage.join(" ")}
              onChange={(e) =>
                setDraft({ ...draft, fsa_coverage: e.target.value.toUpperCase().split(/[\s,]+/).filter(Boolean) })
              }
            />
          </label>
          <div className="flex items-center gap-2 sm:col-span-4">
            <button
              type="button"
              onClick={save}
              className="min-h-10 rounded-xl px-4 text-sm font-semibold text-white"
              style={{ backgroundColor: "var(--primary)" }}
            >
              Save partner
            </button>
            <button type="button" onClick={() => setDraft(null)} className="min-h-10 px-3 text-sm text-muted">
              Cancel
            </button>
            {msg && <span className="text-sm text-muted">{msg}</span>}
          </div>
        </div>
      )}
    </section>
  );
}
