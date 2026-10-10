"use client";

import { useState } from "react";
import { CheckCircle2, Cpu, RefreshCw, Route, Sparkles } from "lucide-react";
import { useApiData } from "@/hooks/useApiData";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import {
  dispatch,
  groupStops,
  minutes,
  money,
  routeMix,
  STOP_KIND_LABEL,
  type FleetPlan,
  type PlanExplanation,
  type PlanRoute,
} from "@/lib/dispatch";
import { cn } from "@porterchain/ui/utils";

const KIND_DOT: Record<string, string> = {
  pickup: "bg-secondary",
  return_pickup: "bg-amber-500",
  drop: "bg-primary",
  return_drop: "bg-amber-700",
  hub: "bg-violet-600",
  handoff: "bg-violet-600",
};

const BTN =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 text-sm font-semibold disabled:opacity-50";

function RouteCard({ r, index, onOpenOrder }: { r: PlanRoute; index: number; onOpenOrder: (id: string) => void }) {
  const fill = Math.min(100, Math.max(0, r.fill_pct));
  return (
    <article className="flex min-w-0 flex-col rounded-2xl border border-primary/10 bg-white" data-testid="plan-route">
      <header className="border-b border-primary/10 p-4">
        <div className="flex items-baseline justify-between gap-2">
          <h3 className="text-base font-semibold text-primary">
            R{index + 1} · <span className="capitalize">{r.vehicle_class.replace("_", " ")}</span>
          </h3>
          <span className="text-sm font-semibold tabular-nums text-primary">{money(r.cost_cents)}</span>
        </div>
        <p className="mt-0.5 truncate text-xs text-muted">
          {r.driver_name ?? "Unassigned vehicle"} · {groupStops(r.stops).length} stops · {routeMix(r.stops)} · {minutes(r.seconds)}
        </p>
        <div className="mt-2 flex items-center gap-2" aria-label={`Fill ${fill}%`}>
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-primary/10">
            <div
              className={cn("h-full rounded-full", fill > 85 ? "bg-red-600" : "bg-secondary")}
              style={{ width: `${fill}%` }}
            />
          </div>
          <span className="w-12 text-right text-xs tabular-nums text-muted">{fill}%</span>
        </div>
      </header>
      <ol className="divide-y divide-primary/5">
        {groupStops(r.stops).map((s, i) => (
          <li key={s.key} className="flex items-center gap-3 px-4 py-2">
            <span className="w-5 text-right text-xs tabular-nums text-muted">{i + 1}</span>
            <span className={cn("h-2.5 w-2.5 shrink-0 rounded-full", KIND_DOT[s.kind] ?? "bg-primary")} aria-hidden />
            <button
              type="button"
              onClick={() => onOpenOrder(s.order_id)}
              className="min-w-0 flex-1 truncate text-left text-sm text-primary hover:underline"
            >
              <span className="font-medium">
                {STOP_KIND_LABEL[s.kind]}
                {s.count > 1 ? ` ×${s.count}` : ""}
              </span>
              <span className="text-muted"> · {s.fsa ?? "—"} · {s.order_number ?? s.order_id.slice(0, 8)}</span>
            </button>
            <span className="text-xs tabular-nums text-muted">+{minutes(s.eta_s)}</span>
          </li>
        ))}
      </ol>
    </article>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-white/60">{label}</p>
      <p className="truncate text-xl font-bold tabular-nums text-white">{value}</p>
    </div>
  );
}

export function FleetPlanPanel({
  tick,
  onOpenOrder,
  onCommitted,
}: {
  tick: number;
  onOpenOrder: (id: string) => void;
  onCommitted: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const { data, refetch } = useApiData((t) => dispatch.latestPlan(t), [tick], { key: "dispatch-plan-latest" });
  const [override, setOverride] = useState<FleetPlan | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [why, setWhy] = useState<PlanExplanation | null>(null);
  const plan = override ?? data?.plan ?? null;

  const run = async (label: string, fn: (t: string) => Promise<FleetPlan>) => {
    setBusy(label);
    setErr(null);
    setWhy(null);
    try {
      setOverride(await fn(await getApiToken()));
      await refetch();
    } catch (e) {
      setErr(e instanceof Error ? e.message : `${label} failed`);
    } finally {
      setBusy(null);
    }
  };

  const explain = async () => {
    if (!plan) return;
    setBusy("Explain");
    try {
      setWhy(await dispatch.explainPlan(await getApiToken(), plan.id));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Explain failed");
    } finally {
      setBusy(null);
    }
  };

  const commit = async () => {
    if (!plan) return;
    const n = plan.routes.filter((r) => r.driver_id).length;
    if (!window.confirm(`Assign ${n} route(s) to their drivers now? Drivers are notified through the normal assign flow.`)) return;
    await run("Commit", (t) => dispatch.commitPlan(t, plan.id));
    onCommitted();
  };

  const s = plan?.summary ?? {};
  const stops = plan?.routes.reduce((a, r) => a + r.stops.length, 0) ?? 0;
  const draft = plan?.status === "draft";
  const compare = Object.entries(s.compare ?? {});

  return (
    <section className="space-y-4" data-testid="fleet-plan">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          disabled={!!busy}
          onClick={() => run("Plan", (t) => dispatch.planDay(t))}
          data-dispatch-shortcut="plan"
          aria-keyshortcuts="P"
          className={cn(BTN, draft ? "border border-primary/15 bg-white text-primary" : "text-white")}
          style={draft ? undefined : { backgroundColor: "var(--primary)" }}
        >
          <Route className="h-4 w-4" />
          {busy === "Plan" ? "Planning…" : draft ? "Plan again" : "Plan the day"}
        </button>
        {plan && plan.status === "committed" && (
          <button
            type="button"
            disabled={!!busy}
            onClick={() => run("Re-plan", (t) => dispatch.replan(t, plan.id))}
            className={cn(BTN, "border border-primary/15 bg-white text-primary")}
          >
            <RefreshCw className="h-4 w-4" />
            {busy === "Re-plan" ? "Re-planning…" : "Re-plan from live"}
          </button>
        )}
        {plan && (
          <button
            type="button"
            disabled={!!busy}
            onClick={explain}
            className={cn(BTN, "border border-primary/15 bg-white text-primary")}
          >
            <Sparkles className="h-4 w-4" />
            {busy === "Explain" ? "Thinking…" : "Explain"}
          </button>
        )}
        {draft && (
          <button
            type="button"
            disabled={!!busy || !plan?.routes.length}
            onClick={commit}
            className={cn(BTN, "ml-auto bg-secondary text-white")}
          >
            <CheckCircle2 className="h-4 w-4" />
            {busy === "Commit" ? "Assigning…" : `Commit ${plan?.routes.length ?? 0} route${plan?.routes.length === 1 ? "" : "s"}`}
          </button>
        )}
      </div>

      {err && <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-800">{err}</p>}

      {!plan && !busy && (
        <div className="rounded-2xl border border-dashed border-primary/20 bg-white p-8 text-center">
          <p className="text-base font-semibold text-primary">No plan yet today</p>
          <p className="mt-1 text-sm text-muted">
            One tap sequences every waiting order across every online vehicle — pickups before drops, under 85% full.
          </p>
        </div>
      )}

      {plan && (
        <>
          <div className="rounded-2xl p-4" style={{ backgroundColor: "var(--primary)" }}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/70">
                Plan v{plan.version} · {plan.status}
                {s.kind === "replan" ? " · re-plan" : ""}
              </p>
              <p className="inline-flex items-center gap-1.5 text-xs text-white/80">
                <Cpu className="h-3.5 w-3.5" />
                {plan.solver === "cuopt" ? "NVIDIA cuOpt" : "OR-Tools"}
                {compare.length > 1 &&
                  ` · ${compare
                    .map(([k, v]) => `${k === "cuopt" ? "cuOpt" : "OR-Tools"} ${v.status ?? money(v.cost_cents)}`)
                    .join(" vs ")}`}
              </p>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-5">
              <Stat label="Vehicles" value={String(s.vehicles_used ?? plan.routes.length)} />
              <Stat label="Stops" value={String(stops)} />
              <Stat label="Orders" value={String(s.orders ?? 0)} />
              <Stat label="Cost" value={money(s.cost_cents ?? 0)} />
              <Stat label="Unplanned" value={String((s.dropped?.length ?? 0) + (s.skipped?.length ?? 0))} />
            </div>
            {s.shapes && Object.keys(s.shapes).length > 0 && (
              <ul className="mt-3 flex flex-wrap gap-1.5">
                {Object.entries(s.shapes).map(([k, n]) => (
                  <li key={k} className="rounded-full bg-white/10 px-2.5 py-0.5 text-xs text-white">
                    {k} × {n}
                  </li>
                ))}
              </ul>
            )}
          </div>

          {s.commit && (
            <p className="rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
              Assigned {s.commit.assigned} order(s)
              {s.commit.skipped.length ? ` · ${s.commit.skipped.length} skipped (${s.commit.skipped[0].reason})` : ""}.
            </p>
          )}

          {why && (
            <div className="rounded-2xl border border-secondary/25 bg-secondary/5 p-4" data-testid="plan-explain">
              <p className="text-xs font-semibold uppercase tracking-wide text-secondary">
                {why.source === "nvidia_nim" ? "NVIDIA NIM · anonymised" : "Rules"} · suggestions only
              </p>
              <ul className="mt-2 space-y-1 text-sm text-primary">
                {why.explanation.map((l) => (
                  <li key={l}>{l}</li>
                ))}
              </ul>
              {why.suggestions.length > 0 && (
                <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-primary">
                  {why.suggestions.map((l) => (
                    <li key={l}>{l}</li>
                  ))}
                </ul>
              )}
              <p className="mt-3 text-xs text-muted">Nothing changes until you commit.</p>
            </div>
          )}

          <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
            {plan.routes.map((r, i) => (
              <RouteCard key={r.id} r={r} index={i} onOpenOrder={onOpenOrder} />
            ))}
          </div>

          {!!s.skipped?.length && (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
              <p className="text-sm font-semibold text-amber-900">Not planned</p>
              <ul className="mt-1 space-y-1 text-sm text-amber-900">
                {s.skipped.map((x) => (
                  <li key={x.order_id}>
                    <button type="button" className="hover:underline" onClick={() => onOpenOrder(x.order_id)}>
                      {x.order_number}
                    </button>{" "}
                    — {x.reason}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </section>
  );
}
