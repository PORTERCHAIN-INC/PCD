"use client";

import { useState } from "react";
import { ArrowRight } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { merchantOps, cad, NEED_TAB, type MerchantOps } from "@/lib/merchant-ops";
import { ScoreRing, BAND_LABEL } from "./ScoreRing";
import { Sparkline } from "./Sparkline";
import { Panel, Skeleton, inputClass } from "./ui";

const SEGMENTS: [string, string][] = [
  ["pharmacy_lab", "Pharmacy & lab"],
  ["shopify", "Shopify stores"],
  ["trades", "Construction & trades"],
  ["warehouse_3pl", "Warehouse & 3PL"],
  ["trader", "Traders & wholesale"],
  ["food", "Food & beverage"],
  ["other", "Other"],
];

/**
 * Numbers first: health, money, volume, revenue. Then one sentence of what to do
 * and the single accent button that does it.
 */
export function MerchantHero({
  ops,
  revenue30dCents,
  orders30d,
  onGo,
}: {
  ops: MerchantOps | undefined;
  revenue30dCents: number;
  orders30d: number;
  onGo: (tab: string, panel?: string) => void;
}) {
  if (!ops) {
    return (
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4" aria-busy="true">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="space-y-2 py-2">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-8 w-28" />
          </div>
        ))}
      </div>
    );
  }
  const h = ops.health;
  const first = h.needs_action[0];
  const target = first ? NEED_TAB[first] : null;
  const change = h.trend.change_pct;
  const owed = h.overdue_cents > 0 ? h.overdue_cents : h.outstanding_cents;
  return (
    <div className="space-y-6">
      <dl className="grid grid-cols-2 gap-x-6 gap-y-5 lg:grid-cols-4">
        <div className="flex items-center gap-3">
          <ScoreRing score={h.score} />
          <div>
            <dt className="text-[11px] font-semibold tracking-[0.14em] text-slate-600 uppercase">
              Health
            </dt>
            <dd
              className={cn(
                "text-lg font-extrabold",
                h.band === "at_risk"
                  ? "text-red-700"
                  : h.band === "watch"
                    ? "text-amber-800"
                    : "text-emerald-700"
              )}
            >
              {BAND_LABEL[h.band]}
            </dd>
          </div>
        </div>
        <Num
          label={h.overdue_cents > 0 ? "Overdue" : "Owed"}
          value={cad(owed)}
          bad={h.overdue_cents > 0}
          hint={
            h.overdue_cents > 0 ? `${cad(h.outstanding_cents)} outstanding` : "Interac e-Transfer"
          }
        />
        <div className="min-w-0">
          <dt className="text-[11px] font-semibold tracking-[0.14em] text-slate-600 uppercase">
            Orders · 4 wk
          </dt>
          <dd className="mt-1 flex items-center gap-3">
            <span className="text-3xl font-extrabold tracking-tight text-primary tabular-nums">
              {h.trend.last_4w}
            </span>
            <span className="hidden sm:inline">
              <Sparkline values={h.trend.weekly} width={84} height={28} />
            </span>
          </dd>
          <dd
            className={cn(
              "text-xs",
              change != null && change < 0 ? "text-red-700" : "text-slate-600"
            )}
          >
            {change != null
              ? `${change > 0 ? "+" : ""}${change}% vs prior 4 wk`
              : "No prior period"}
          </dd>
        </div>
        <Num label="Revenue · 30 d" value={cad(revenue30dCents)} hint={`${orders30d} orders`} />
      </dl>

      {(target || ops.needs_labels.length > 0) && (
        <div className="flex flex-col gap-4 rounded-3xl bg-primary px-5 py-5 text-white sm:flex-row sm:items-center sm:px-6">
          <div className="min-w-0 flex-1">
            <p className="text-[11px] font-semibold tracking-[0.18em] text-white/70 uppercase">
              Next action
            </p>
            <p className="mt-1 text-lg font-bold sm:text-xl">{h.next_action}</p>
            {ops.needs_labels.length > 0 ? (
              <p className="mt-1 text-sm text-white/75">{ops.needs_labels.join(" · ")}</p>
            ) : null}
          </div>
          {target ? (
            <button
              type="button"
              className="inline-flex min-h-11 w-full shrink-0 items-center justify-center gap-2 rounded-full bg-white px-5 text-sm font-bold shadow-sm hover:bg-white/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white sm:w-auto"
              // Inline colour: an unlayered `button { color }` rule in the shared CSS beats utilities here.
              style={{ color: "var(--primary, #0a1628)" }}
              onClick={() => onGo(target.tab, target.panel)}
            >
              Do it now <ArrowRight className="h-4 w-4" aria-hidden />
            </button>
          ) : null}
        </div>
      )}
    </div>
  );
}

function Num({
  label,
  value,
  hint,
  bad,
}: {
  label: string;
  value: string;
  hint?: string;
  bad?: boolean;
}) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] font-semibold tracking-[0.14em] text-slate-600 uppercase">
        {label}
      </dt>
      <dd
        className={cn(
          "mt-1 truncate text-3xl font-extrabold tracking-tight tabular-nums",
          bad ? "text-red-700" : "text-primary"
        )}
      >
        {value}
      </dd>
      {hint ? <dd className="truncate text-xs text-slate-600">{hint}</dd> : null}
    </div>
  );
}

export function HealthReasons({ ops }: { ops: MerchantOps }) {
  const h = ops.health;
  return (
    <Panel
      title={<span id="why-score">Why {h.score}</span>}
      aside={<span className="text-sm font-semibold text-slate-600 tabular-nums">out of 100</span>}
    >
      {h.reasons.length === 0 ? (
        <p className="text-sm text-slate-600">
          No signals yet. The score fills in after the first orders.
        </p>
      ) : (
        <ul className="-my-2 divide-y divide-primary/5">
          {h.reasons.map((r) => (
            <li key={r.label} className="flex items-center justify-between gap-3 py-2.5 text-sm">
              <span className="min-w-0 text-primary">{r.label}</span>
              <span
                className={cn(
                  "shrink-0 font-bold tabular-nums",
                  r.points < 0 ? "text-red-700" : "text-emerald-700"
                )}
              >
                {r.points > 0 ? `+${r.points}` : r.points}
              </span>
            </li>
          ))}
        </ul>
      )}
      <dl className="mt-5 grid grid-cols-2 gap-4 border-t border-primary/5 pt-5 sm:grid-cols-4">
        <Fact
          label="Last order"
          value={h.days_since_last_order == null ? "Never" : `${h.days_since_last_order} d ago`}
        />
        <Fact label="Usual gap" value={h.usual_gap_days == null ? "—" : `${h.usual_gap_days} d`} />
        <Fact label="On time · 30 d" value={h.on_time_pct == null ? "—" : `${h.on_time_pct}%`} />
        <Fact
          label="Open issues"
          value={String(h.open_tickets + h.open_claims + h.open_exceptions)}
        />
      </dl>
    </Panel>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-slate-600">{label}</dt>
      <dd className="truncate text-base font-bold text-primary tabular-nums">{value}</dd>
    </div>
  );
}

/** Account owner + segment. Saved on change. */
export function OwnerSegmentCard({ ops, onSaved }: { ops: MerchantOps; onSaved: () => void }) {
  const { getApiToken } = useAdminAuth();
  const { data: owners } = useApiData((t) => merchantOps.owners(t), [], { key: "merchant-owners" });
  const [err, setErr] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function save(kind: "owner" | "segment", value: string) {
    setBusy(true);
    setErr(null);
    setSaved(null);
    try {
      const t = await getApiToken();
      if (kind === "owner") await merchantOps.setOwner(t, ops.merchant_id, value || null);
      else await merchantOps.setSegment(t, ops.merchant_id, value || null);
      setSaved(kind === "owner" ? "Owner saved" : "Segment saved");
      onSaved();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Panel
      title="Account"
      aside={
        <span
          role="status"
          className={cn("text-xs font-semibold", err ? "text-red-700" : "text-emerald-700")}
        >
          {err ?? saved ?? ""}
        </span>
      }
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="mb-1.5 block text-sm font-semibold text-primary">Owner</span>
          <select
            className={inputClass}
            value={ops.owner.id ?? ""}
            disabled={busy}
            onChange={(e) => void save("owner", e.target.value)}
          >
            <option value="">Unassigned</option>
            {(owners ?? []).map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="mb-1.5 block text-sm font-semibold text-primary">Segment</span>
          <select
            className={inputClass}
            value={ops.segment.tags[0] ?? ""}
            disabled={busy}
            onChange={(e) => void save("segment", e.target.value)}
          >
            <option value="">Auto · {ops.segment.label}</option>
            {SEGMENTS.map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </label>
      </div>
    </Panel>
  );
}
