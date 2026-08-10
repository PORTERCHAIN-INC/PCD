"use client";

import { useState } from "react";
import { Gauge, Play, Upload } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { ops, type OptimizeAssignment, type OptimizeRunResult } from "@/lib/operations";
import { Badge, Button, EmptyState, SectionCard, Spinner } from "@/components/crm/primitives";

function Metric({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-primary/10 bg-gray-bg/40 px-3 py-2">
      <p className="text-[11px] font-medium uppercase tracking-wide text-muted">{label}</p>
      <p className="text-lg font-semibold text-primary">{value}</p>
      {hint && <p className="text-[11px] text-muted">{hint}</p>}
    </div>
  );
}

export function OptimizePanel({
  tick,
  onOpenOrder,
  onCommitted,
}: {
  tick: number;
  onOpenOrder: (id: string) => void;
  onCommitted: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const { data: pool, loading: poolLoading } = useApiData((t) => ops.optimizePool(t), [tick], {
    key: "ops-optimize-pool",
  });
  const [engine, setEngine] = useState("greedy");
  const [mode, setMode] = useState("allocate");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<OptimizeRunResult | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const token = await getApiToken();
      const result = await ops.optimizeRun(token, { mode, engine });
      setPlan(result);
      if (!result.ok && result.error) setError(result.error);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Run failed");
    } finally {
      setBusy(false);
    }
  }

  async function commit() {
    if (!plan?.assignments?.length) return;
    setBusy(true);
    setError(null);
    try {
      const token = await getApiToken();
      const result = await ops.optimizeCommit(token, plan.assignments);
      if (!result.ok) {
        setError(result.error || "Commit failed");
      } else {
        setPlan(null);
        onCommitted();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Commit failed");
    } finally {
      setBusy(false);
    }
  }

  const m = plan?.metrics;

  return (
    <div className="space-y-4">
      <SectionCard
        title={
          <span className="flex items-center gap-2">
            <Gauge className="h-4 w-4 text-secondary" /> Optimize (Fleetbase Orchestrator)
          </span>
        }
        action={
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              className="rounded-lg border border-primary/15 px-2 py-1 text-xs"
            >
              <option value="allocate">Allocate</option>
              <option value="assign_vehicles">Assign vehicles</option>
              <option value="assign_drivers">Assign drivers</option>
              <option value="optimize_routes">Optimize routes</option>
            </select>
            <select
              value={engine}
              onChange={(e) => setEngine(e.target.value)}
              className="rounded-lg border border-primary/15 px-2 py-1 text-xs"
            >
              <option value="greedy">Greedy</option>
              <option value="vroom">VROOM</option>
            </select>
            <Button onClick={() => void run()} disabled={busy} className="text-xs">
              <Play className="h-3.5 w-3.5" /> {busy ? "Running…" : "Run preview"}
            </Button>
            <Button
              variant="outline"
              onClick={() => void commit()}
              disabled={busy || !plan?.assignments?.length}
              className="text-xs"
            >
              <Upload className="h-3.5 w-3.5" /> Commit manifests
            </Button>
          </div>
        }
      >
        <div className="space-y-4 p-4">
          <p className="text-xs text-muted">
            Preview assigns via Fleetbase engines (greedy/VROOM). Commit creates vehicle manifests —
            does not rebuild dispatch in PorterChain.
          </p>
          {error && (
            <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
              {plan?.hint ? ` — ${plan.hint}` : ""}
            </p>
          )}

          {poolLoading && !pool ? (
            <Spinner />
          ) : (
            <p className="text-xs text-primary">
              Pool: {pool?.order_count ?? 0} synced order
              {(pool?.order_count ?? 0) === 1 ? "" : "s"} ready for orchestrator
              {(plan?.missing_sync?.length ?? 0) > 0
                ? ` · ${plan?.missing_sync?.length} selected without Fleetbase sync`
                : ""}
            </p>
          )}

          {m && (
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              <Metric
                label="After distance"
                value={`${m.after_distance_km ?? 0} km`}
                hint="Proposed plan"
              />
              <Metric
                label="After duration"
                value={`${m.after_duration_min ?? 0} min`}
                hint="Proposed plan"
              />
              <Metric
                label="Utilization"
                value={String(m.utilization_orders_per_vehicle ?? "—")}
                hint="Orders / vehicle"
              />
              <Metric
                label="Assigned / unassigned"
                value={`${m.assigned_count ?? 0} / ${m.unassigned_count ?? 0}`}
                hint={`${m.vehicles_used ?? 0} vehicles`}
              />
            </div>
          )}

          {!plan?.assignments?.length ? (
            <EmptyState
              title="No plan yet"
              hint="Run preview against the synced pool. Orders need fleetbase_order_id."
            />
          ) : (
            <div className="overflow-x-auto rounded-xl border border-primary/10">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-gray-bg/60 text-xs uppercase text-muted">
                  <tr>
                    <th className="px-3 py-2">Order</th>
                    <th className="px-3 py-2">Vehicle</th>
                    <th className="px-3 py-2">Driver</th>
                    <th className="px-3 py-2">Km</th>
                    <th className="px-3 py-2">Min</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-primary/5">
                  {plan.assignments.map((a: OptimizeAssignment, i: number) => (
                    <tr key={`${a.order_id}-${i}`} className="hover:bg-gray-bg/40">
                      <td className="px-3 py-2">
                        {a.porterchain_order_id ? (
                          <button
                            type="button"
                            className="font-medium text-secondary hover:underline"
                            onClick={() => onOpenOrder(a.porterchain_order_id!)}
                          >
                            {a.order_id}
                          </button>
                        ) : (
                          a.order_id
                        )}
                      </td>
                      <td className="px-3 py-2 text-muted">{a.vehicle_id || "—"}</td>
                      <td className="px-3 py-2 text-muted">{a.driver_id || "—"}</td>
                      <td className="px-3 py-2">
                        {a.distance_m != null ? (a.distance_m / 1000).toFixed(1) : "—"}
                      </td>
                      <td className="px-3 py-2">
                        {a.duration_s != null ? Math.round(a.duration_s / 60) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {!!plan?.unassigned?.length && (
            <div className="flex flex-wrap gap-1">
              <span className="text-xs text-muted">Unassigned:</span>
              {plan.unassigned.map((id) => (
                <Badge key={id} tone="amber">
                  {id}
                </Badge>
              ))}
            </div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
