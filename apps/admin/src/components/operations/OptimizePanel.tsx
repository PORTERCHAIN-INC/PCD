"use client";

import { useEffect, useEffectEvent, useRef, useState } from "react";
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
  const { data: enginesPayload } = useApiData((t) => ops.optimizeEngines(t), [tick], {
    key: "ops-optimize-engines",
  });
  const engineOptions = (() => {
    const raw = enginesPayload?.engines ?? [];
    const ids = raw.map((e) => String(e.id || e.name || "").trim()).filter(Boolean);
    return ids.length ? ids : ["porterchain"];
  })();
  const [engine, setEngine] = useState("porterchain");
  useEffect(() => {
    if (engineOptions.length && !engineOptions.includes(engine)) {
      setEngine(engineOptions[0]);
    }
  }, [engineOptions, engine]);
  const [mode, setMode] = useState("allocate");
  const [shape, setShape] = useState<"fleet" | "merchant" | "vehicle">("fleet");
  const [merchantId, setMerchantId] = useState<string>("");
  const [vehicleId, setVehicleId] = useState<string>("");
  const [pageOffset, setPageOffset] = useState(0);
  const [commitBusy, setCommitBusy] = useState(false);
  const [runBusy, setRunBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<OptimizeRunResult | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const polls = useRef(0);

  const tickStatus = useEffectEvent(async (cancelled: { current: boolean }) => {
    polls.current += 1;
    try {
      const token = await getApiToken();
      const result = await ops.optimizeRunStatus(token, runId!);
      if (cancelled.current) return;
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
      if (cancelled.current) return;
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
      if (cancelled.current) return;
      setError("Preview timed out. Try again.");
      setRunBusy(false);
      setRunId(null);
    }
  });

  useEffect(() => {
    if (!runId) return;
    const cancelled = { current: false };
    polls.current = 0;
    void tickStatus(cancelled);
    const id = window.setInterval(() => void tickStatus(cancelled), POLL_MS);
    return () => {
      cancelled.current = true;
      window.clearInterval(id);
    };
  }, [runId]);

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
        offset: pageOffset,
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

  const capacityBlocked =
    (plan?.metrics?.capacity_reject_count ?? 0) > 0 && (plan?.unassigned?.length ?? 0) > 0;

  async function commit() {
    if (!plan?.assignments?.length || plan.status === "pending" || capacityBlocked) return;
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
  const engineLabel = engine === "insertion" ? "Quick insert" : "PorterChain";
  const emptyHint = readyEmpty
    ? plan?.message ||
      "No stops could be ordered. Check the van, the coordinates, and the time window, then retry."
    : "Preview orders one assigned van. Pickup stays before dropoff.";

  return (
    <div className="space-y-4">
      <SectionCard
        title={
          <span className="flex items-center gap-2">
            <Gauge className="h-4 w-4 text-secondary" /> Optimize
          </span>
        }
        action={
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={shape}
              onChange={(e) => setShape(e.target.value as "fleet" | "merchant" | "vehicle")}
              className="rounded-lg border border-primary/15 px-2 py-1 text-xs"
              title="Which orders to include"
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
              {engineOptions.map((id) => (
                <option key={id} value={id}>
                  {id === "porterchain" || id === "ortools" || id === "vroom"
                    ? "PorterChain"
                    : id === "insertion" || id === "greedy"
                      ? "Quick insert"
                      : id === "capacity"
                        ? "Capacity"
                        : id}
                </option>
              ))}
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
            {(pool?.eligible_count ?? 0) > pageOffset + 20 && (
              <Button
                variant="ghost"
                className="text-xs"
                disabled={runBusy}
                onClick={() => setPageOffset((n) => n + 20)}
              >
                Next 20
              </Button>
            )}
            <Button
              variant="outline"
              onClick={() => void commit()}
              disabled={commitBusy || !ready || capacityBlocked}
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
            Preview orders one assigned van with Valhalla drive times. Accept stores that stop
            order. It does not search again.
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
            <>
              <p className="text-xs text-primary">
                Pool: {pool?.eligible_count ?? pool?.order_count ?? 0} eligible. This preview packs
                20 starting at {pageOffset}.
                {(pool?.excluded?.missing_coords ?? 0) > 0
                  ? ` · ${pool?.excluded?.missing_coords} without coordinates`
                  : ""}
                {(pool?.excluded?.sandbox ?? 0) > 0 ? ` · ${pool?.excluded?.sandbox} sandbox` : ""}
                {(pool?.excluded?.shopify_ingress_paused ?? 0) > 0
                  ? ` · ${pool?.excluded?.shopify_ingress_paused} paused Shopify`
                  : ""}
              </p>
              {capacityBlocked && (
                <p className="text-xs text-red-700">
                  Capacity rejects left stops unassigned. Fix the van load before commit.
                </p>
              )}
            </>
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

          {pending ? (
            <Spinner label="Building the day plan…" />
          ) : !plan ? (
            <EmptyState
              title="No plan yet"
              hint="Run preview against the synced pool. Assign a van, then preview its stops."
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
              <span className="text-xs text-muted">Left off the plan:</span>
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
