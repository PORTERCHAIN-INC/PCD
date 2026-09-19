"use client";

import { useEffect, useRef, useState } from "react";
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

const POLL_MS = 1000;
const POLL_MAX = 45;

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
  const [engine, setEngine] = useState("vroom");
  const [mode, setMode] = useState("allocate");
  const [shape, setShape] = useState<"fleet" | "merchant" | "vehicle">("fleet");
  const [merchantId, setMerchantId] = useState<string>("");
  const [vehicleId, setVehicleId] = useState<string>("");
  const [runBusy, setRunBusy] = useState(false);
  const [commitBusy, setCommitBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<OptimizeRunResult | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const polls = useRef(0);

  useEffect(() => {
    if (!runId) return;
    let cancelled = false;
    polls.current = 0;

    async function tickStatus() {
      polls.current += 1;
      try {
        const token = await getApiToken();
        const result = await ops.optimizeRunStatus(token, runId!);
        if (cancelled) return;
        setPlan(result);
        if (result.status === "ready" || result.status === "error") {
          setRunBusy(false);
          setRunId(null);
          if (result.status === "error") {
            setError(result.error || result.message || "Preview failed");
          }
          return;
        }
      } catch (e) {
        if (cancelled) return;
        const msg = e instanceof Error ? e.message : "";
        if (msg.includes("optimize_run_not_found") && polls.current < POLL_MAX) {
          return;
        }
        setError(msg || "Could not read preview status");
        setRunBusy(false);
        setRunId(null);
        return;
      }
      if (polls.current >= POLL_MAX) {
        if (cancelled) return;
        setError("Preview timed out. Try again.");
        setRunBusy(false);
        setRunId(null);
      }
    }

    void tickStatus();
    const id = window.setInterval(() => void tickStatus(), POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [runId, getApiToken]);

  async function run() {
    setRunBusy(true);
    setError(null);
    try {
      const token = await getApiToken();
      const result = await ops.optimizeRun(token, {
        mode,
        engine,
        shape,
        merchant_id: shape === "merchant" && merchantId ? merchantId : undefined,
        vehicle_ids: shape === "vehicle" && vehicleId ? [vehicleId] : undefined,
      });
      setPlan(result);
      if (result.status === "pending" && result.run_id) {
        setRunId(result.run_id);
        return;
      }
      setRunBusy(false);
      if (result.status === "error" || (!result.ok && result.error)) {
        setError(result.error || result.message || "Run failed");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Run failed");
      setRunBusy(false);
    }
  }

  async function commit() {
    if (!plan?.assignments?.length || plan.status === "pending") return;
    setCommitBusy(true);
    setError(null);
    try {
      const token = await getApiToken();
      const result = await ops.optimizeCommit(token, plan.assignments, {
        runId: plan.run_id || null,
      });
      if (!result.ok) {
        setError(result.error || "Commit failed");
      } else {
        setPlan(null);
        onCommitted();
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Commit failed";
      setError(msg);
      if (msg.includes("Sequence conflict")) {
        setPlan(null);
      }
    } finally {
      setCommitBusy(false);
    }
  }

  function discardPreview() {
    setPlan(null);
    setRunId(null);
    setRunBusy(false);
    setError(null);
  }

  const m = plan?.metrics;
  const pending = plan?.status === "pending" || Boolean(runId);
  const ready = plan?.status === "ready" && Boolean(plan.assignments?.length);
  const readyEmpty = plan?.status === "ready" && !plan.assignments?.length;
  const engineLabel = engine === "vroom" ? "Fleetbase VROOM" : "Fleetbase greedy";
  const emptyHint = readyEmpty
    ? plan?.message ||
      "Fleetbase returned no assignments. Sync cargo vans, mark drivers online, and retry."
    : "Run preview against the synced pool. Orders need a live Fleetbase id (not fb-123).";

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
              value={shape}
              onChange={(e) => setShape(e.target.value as "fleet" | "merchant" | "vehicle")}
              className="rounded-lg border border-primary/15 px-2 py-1 text-xs"
              title="Fleetbase input shaping only"
            >
              <option value="fleet">Fleet-wide</option>
              <option value="merchant">Merchant-wise</option>
              <option value="vehicle">Vehicle-wise</option>
            </select>
            {shape === "merchant" && (
              <select
                value={merchantId}
                onChange={(e) => setMerchantId(e.target.value)}
                className="rounded-lg border border-primary/15 px-2 py-1 text-xs"
              >
                <option value="">Select merchant…</option>
                {(pool?.merchants || [])
                  .filter((m) => m.merchant_id)
                  .map((m) => (
                    <option key={m.merchant_id!} value={m.merchant_id!}>
                      {m.merchant_id} ({m.order_count})
                    </option>
                  ))}
              </select>
            )}
            {shape === "vehicle" && (
              <select
                value={vehicleId}
                onChange={(e) => setVehicleId(e.target.value)}
                className="rounded-lg border border-primary/15 px-2 py-1 text-xs"
              >
                <option value="">Select vehicle…</option>
                {(pool?.vehicle_ids || []).map((id) => (
                  <option key={id} value={id}>
                    {id}
                  </option>
                ))}
              </select>
            )}
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
              <option value="vroom">VROOM</option>
              <option value="greedy">Greedy</option>
              <option value="capacity">Capacity</option>
            </select>
            <Button
              onClick={() => void run()}
              disabled={
                runBusy ||
                (shape === "merchant" && !merchantId) ||
                (shape === "vehicle" && !vehicleId)
              }
              className="text-xs"
            >
              <Play className="h-3.5 w-3.5" /> {runBusy ? "Building plan…" : "Run preview"}
            </Button>
            <Button
              variant="outline"
              onClick={() => void commit()}
              disabled={commitBusy || !ready}
              className="text-xs"
            >
              <Upload className="h-3.5 w-3.5" /> Commit manifests
            </Button>
            {(plan || runId) && (
              <Button
                variant="ghost"
                onClick={discardPreview}
                disabled={commitBusy || runBusy}
                className="text-xs"
                title="Keep current manifests — discard uncommitted preview"
              >
                Discard preview
              </Button>
            )}
          </div>
        }
      >
        <div className="space-y-4 p-4">
          <p className="text-xs text-muted">
            Preview shapes Fleetbase inputs only (fleet / merchant / vehicle). Engines stay on
            Fleetbase (VROOM default). Commit creates vehicle manifests — no PorterChain pathing.
          </p>
          {pending && (
            <p className="rounded-xl border border-primary/15 bg-gray-bg/40 px-3 py-2 text-sm text-primary">
              Building plan ({engineLabel})…
            </p>
          )}
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
              {(pool?.placeholder_skipped ?? 0) > 0
                ? ` · ${pool?.placeholder_skipped} placeholder ids skipped`
                : ""}
              {(plan?.missing_sync?.length ?? 0) > 0
                ? ` · ${plan?.missing_sync?.length} selected without Fleetbase sync`
                : ""}
            </p>
          )}

          {m && (ready || readyEmpty) && (
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
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
                label="Est. fuel"
                value={
                  m.estimated_fuel_cents != null
                    ? `$${(m.estimated_fuel_cents / 100).toFixed(2)}`
                    : "—"
                }
                hint={
                  m.estimated_fuel_liters != null
                    ? `${m.estimated_fuel_liters} L · ${m.valhalla_costing || "auto"} costing`
                    : "pricing_fuel × km"
                }
              />
              <Metric
                label="Fuel / km"
                value={m.cents_per_km != null ? `${m.cents_per_km.toFixed(1)} ¢` : "—"}
                hint={m.liters_per_100km != null ? `${m.liters_per_100km} L/100km` : "Estimate"}
              />
              <Metric
                label="Utilization"
                value={String(m.utilization_orders_per_vehicle ?? "—")}
                hint="Orders / vehicle"
              />
              <Metric
                label="Assigned / unassigned"
                value={`${m.assigned_count ?? 0} / ${m.unassigned_count ?? 0}`}
                hint={
                  (m.capacity_reject_count ?? 0) > 0
                    ? `${m.capacity_reject_count} capacity rejects · ${m.vehicles_used ?? 0} vehicles`
                    : `${m.vehicles_used ?? 0} vehicles`
                }
              />
            </div>
          )}

          {m?.cuopt_shadow && (ready || readyEmpty) && (
            <p className="rounded-xl border border-primary/10 bg-gray-bg/40 px-3 py-2 text-xs text-primary">
              cuOpt shadow: {m.cuopt_shadow.status}
              {m.cuopt_shadow.winner ? ` · winner ${m.cuopt_shadow.winner}` : ""}
              {m.cuopt_shadow.vroom_distance_km != null && m.cuopt_shadow.cuopt_distance_km != null
                ? ` · VROOM ${m.cuopt_shadow.vroom_distance_km} km vs cuOpt ${m.cuopt_shadow.cuopt_distance_km} km`
                : ""}
              {m.cuopt_shadow.reason ? ` · ${m.cuopt_shadow.reason}` : ""}
              {" · commit stays Fleetbase VROOM"}
            </p>
          )}

          {pending ? (
            <Spinner label="Building plan from Fleetbase…" />
          ) : !plan ? (
            <EmptyState
              title="No plan yet"
              hint="Run preview against the synced pool. Orders need a live Fleetbase id."
            />
          ) : !plan.assignments?.length ? (
            <EmptyState title={readyEmpty ? "No assignments" : "No plan yet"} hint={emptyHint} />
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

          {!!plan?.unassigned_details?.length && ready && (
            <div className="space-y-1">
              <span className="text-xs text-muted">Unassigned (Fleetbase reasons):</span>
              <div className="flex flex-wrap gap-1">
                {plan.unassigned_details.map((row) => (
                  <Badge
                    key={row.order_id}
                    tone={
                      (row.reason || "").toLowerCase().includes("capacity") ||
                      (row.reason || "").toLowerCase().includes("vehicle")
                        ? "red"
                        : "amber"
                    }
                  >
                    {row.order_id}
                    {row.reason ? ` · ${row.reason}` : ""}
                  </Badge>
                ))}
              </div>
            </div>
          )}
          {!plan?.unassigned_details?.length && !!plan?.unassigned?.length && ready && (
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
