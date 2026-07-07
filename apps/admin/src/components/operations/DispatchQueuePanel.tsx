"use client";

import { useMemo, useState } from "react";
import { Route, Users } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { api } from "@/lib/api";
import {
  ops,
  type AssignableDriver,
  type AssignBatchResponse,
  type OptimizedStop,
  type OptimizeQueueResponse,
  type QueueOrder,
} from "@/lib/operations";
import {
  Badge,
  Button,
  EmptyState,
  SectionCard,
  Select,
  Spinner,
} from "@/components/crm/primitives";
import { titleCase } from "@/lib/crmFormat";

function SlaBadge({ sla }: { sla: string }) {
  const tone = sla === "breached" ? "red" : sla === "at_risk" ? "amber" : "green";
  return <Badge tone={tone}>{titleCase(sla)}</Badge>;
}

function stopKey(s: OptimizedStop) {
  return `${s.order_id}:${s.sequence}:${s.type}`;
}

/** Linked stops for the same parcel (pickup ↔ delivery). */
function linkedStopKeys(
  stops: OptimizedStop[],
  stop: OptimizedStop,
  mode: "check" | "uncheck"
): string[] {
  const keys: string[] = [stopKey(stop)];
  const siblings = stops.filter((s) => s.order_id === stop.order_id && s.type !== stop.type);
  for (const s of siblings) {
    if (mode === "check") {
      keys.push(stopKey(s));
    } else if (stop.type === "pickup" && s.type === "delivery") {
      // Unchecking pickup also clears delivery for that parcel.
      keys.push(stopKey(s));
    }
  }
  return keys;
}

type Props = {
  tick: number;
  onAssigned: () => void;
};

export function DispatchQueuePanel({ tick, onAssigned }: Props) {
  const { getApiToken } = useAdminAuth();
  const { data, loading, error, refetch, isFetching } = useApiData((t) => ops.queue(t), [tick], {
    key: "ops-queue",
  });
  const { data: driversList, loading: driversLoading } = useApiData(
    (t) => ops.assignableDrivers(t),
    [tick],
    { key: "ops-assignable-drivers" }
  );

  const [queueSelected, setQueueSelected] = useState<string[]>([]);
  const [optimizedSelected, setOptimizedSelected] = useState<string[]>([]);
  const [choice, setChoice] = useState<Record<string, string>>({});
  const [batchDriverId, setBatchDriverId] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [optimizing, setOptimizing] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [optimizeResult, setOptimizeResult] = useState<OptimizeQueueResponse | null>(null);
  const [assignResult, setAssignResult] = useState<AssignBatchResponse | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const orders = data ?? [];
  const allQueueIds = orders.map((o) => o.id);
  const allQueueSelected = allQueueIds.length > 0 && queueSelected.length === allQueueIds.length;

  const optimizedStops = optimizeResult?.optimized_stops ?? [];
  const allStopKeys = optimizedStops.map(stopKey);
  const allOptimizedSelected =
    allStopKeys.length > 0 && optimizedSelected.length === allStopKeys.length;

  const selectedOrderIds = useMemo(() => {
    const ids = new Set<string>();
    for (const key of optimizedSelected) {
      const stop = optimizedStops.find((s) => stopKey(s) === key);
      if (stop) ids.add(stop.order_id);
    }
    return [...ids];
  }, [optimizedSelected, optimizedStops]);

  function toggleQueue(id: string) {
    setQueueSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  function toggleAllQueue() {
    setQueueSelected(allQueueSelected ? [] : allQueueIds);
  }

  function toggleOptimized(key: string) {
    const stop = optimizedStops.find((s) => stopKey(s) === key);
    if (!stop) return;

    setOptimizedSelected((prev) => {
      const isChecking = !prev.includes(key);
      const next = new Set(prev);
      const keys = linkedStopKeys(optimizedStops, stop, isChecking ? "check" : "uncheck");
      for (const k of keys) {
        if (isChecking) next.add(k);
        else next.delete(k);
      }
      return [...next];
    });
  }

  function toggleAllOptimized() {
    setOptimizedSelected(allOptimizedSelected ? [] : allStopKeys);
  }

  async function assignSingle(orderId: string) {
    const driverId = choice[orderId];
    if (!driverId) return;
    setBusy(orderId);
    setActionError(null);
    try {
      const token = await getApiToken();
      await api.assignDriver(token, orderId, driverId);
      onAssigned();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Assign failed");
    } finally {
      setBusy(null);
    }
  }

  async function optimizeSelected() {
    if (queueSelected.length < 2) return;
    setOptimizing(true);
    setActionError(null);
    setAssignResult(null);
    try {
      const token = await getApiToken();
      const result = await ops.optimizeQueue(token, queueSelected);
      setOptimizeResult(result);
      setOptimizedSelected(result.optimized_stops.map(stopKey));
    } catch (e) {
      setOptimizeResult(null);
      setOptimizedSelected([]);
      setActionError(e instanceof Error ? e.message : "Optimize failed");
    } finally {
      setOptimizing(false);
    }
  }

  async function assignBatch() {
    if (!optimizeResult?.plan_id || !batchDriverId || selectedOrderIds.length === 0) return;
    setAssigning(true);
    setActionError(null);
    try {
      const token = await getApiToken();
      const result = await ops.assignBatch(token, {
        plan_id: optimizeResult.plan_id,
        driver_id: batchDriverId,
        order_ids: selectedOrderIds,
      });
      setAssignResult(result);
      setQueueSelected([]);
      setOptimizedSelected([]);
      setOptimizeResult(null);
      setBatchDriverId("");
      onAssigned();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Batch assign failed");
    } finally {
      setAssigning(false);
    }
  }

  const online = (driversList ?? []).filter((d) => d.online);

  if (loading && !data) {
    return (
      <SectionCard title="Dispatch queue">
        <Spinner label="Loading dispatch queue…" />
      </SectionCard>
    );
  }

  if (error) {
    return (
      <SectionCard title="Dispatch queue">
        <div className="space-y-3 px-5 py-6 text-center">
          <p className="text-sm text-red-600">Could not load dispatch queue: {error}</p>
          <Button variant="outline" onClick={() => void refetch()} disabled={isFetching}>
            {isFetching ? "Retrying…" : "Retry"}
          </Button>
        </div>
      </SectionCard>
    );
  }

  return (
    <div className="space-y-3">
      {(actionError || assignResult) && (
        <div className="space-y-2">
          {actionError && (
            <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
              {actionError}
            </p>
          )}
          {assignResult && (
            <p className="rounded-xl border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-800">
              Assigned {assignResult.assigned_count} parcel(s) to driver.
              {assignResult.errors.length > 0
                ? ` ${assignResult.errors.length} error(s) — check individual orders.`
                : null}
            </p>
          )}
        </div>
      )}

      <div className="grid min-h-[560px] grid-cols-1 gap-4 xl:grid-cols-2">
        {/* Left — dispatch pool */}
        <SectionCard
          title={`Dispatch queue (${orders.length})`}
          action={
            <span className="text-xs text-muted">
              {driversLoading ? "Loading drivers…" : `${online.length} online`}
            </span>
          }
          className="flex h-full flex-col"
        >
          {queueSelected.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 border-b border-primary/10 px-4 py-3">
              <span className="text-sm font-medium text-primary">
                {queueSelected.length} selected
              </span>
              <Button
                variant="outline"
                className="gap-2"
                onClick={() => void optimizeSelected()}
                disabled={queueSelected.length < 2 || optimizing}
              >
                <Route className="h-4 w-4" />
                {optimizing ? "Optimizing…" : "Optimize route"}
              </Button>
            </div>
          )}

          <div className="min-h-0 flex-1 overflow-y-auto">
            {orders.length === 0 ? (
              <EmptyState title="Queue is clear" hint="No unassigned orders awaiting dispatch." />
            ) : (
              <div className="divide-y divide-primary/5">
                <label className="flex cursor-pointer items-center gap-3 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-muted">
                  <input
                    type="checkbox"
                    checked={allQueueSelected}
                    onChange={toggleAllQueue}
                    className="h-4 w-4 rounded border-primary/20 text-secondary"
                  />
                  Select all
                </label>
                {orders.map((o: QueueOrder) => {
                  const missingCoords =
                    o.stop_phase === "delivery_only"
                      ? !o.has_dropoff_coords
                      : !o.has_pickup_coords || !o.has_dropoff_coords;
                  return (
                    <div
                      key={o.id}
                      className={cn(
                        "flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between",
                        queueSelected.includes(o.id) && "bg-secondary/[0.04]"
                      )}
                    >
                      <div className="flex min-w-0 items-start gap-3">
                        <input
                          type="checkbox"
                          checked={queueSelected.includes(o.id)}
                          onChange={() => toggleQueue(o.id)}
                          className="mt-1 h-4 w-4 shrink-0 rounded border-primary/20 text-secondary"
                        />
                        <div className="min-w-0">
                          <p className="flex flex-wrap items-center gap-2 font-mono text-xs font-semibold text-primary">
                            <span>{o.tracking_number}</span>
                            {o.high_priority ? <Badge tone="red">High</Badge> : null}
                            <Badge tone="slate">{titleCase(o.state)}</Badge>
                            {missingCoords ? <Badge tone="amber">Missing coords</Badge> : null}
                          </p>
                          <p className="truncate text-xs text-muted">
                            {o.merchant ?? "—"} · {o.pickup ?? "?"} → {o.dropoff ?? "?"}
                          </p>
                        </div>
                      </div>
                      <div className="flex shrink-0 items-center gap-2 pl-7 sm:pl-0">
                        <SlaBadge sla={o.sla} />
                        <Select
                          value={choice[o.id] ?? ""}
                          onChange={(e) => setChoice({ ...choice, [o.id]: e.target.value })}
                          className="w-40"
                        >
                          <option value="">Driver…</option>
                          {(driversList ?? []).map((d: AssignableDriver) => (
                            <option key={d.id} value={d.id}>
                              {d.name}
                              {d.online ? " ●" : ""}
                            </option>
                          ))}
                        </Select>
                        <Button
                          className="shrink-0 px-3 py-1.5 text-xs"
                          onClick={() => void assignSingle(o.id)}
                          disabled={!choice[o.id] || busy === o.id}
                        >
                          Assign
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </SectionCard>

        {/* Right — optimized route */}
        <SectionCard
          title={
            optimizeResult
              ? `Optimized route (${optimizedStops.length} stops · ${selectedOrderIds.length} parcel${selectedOrderIds.length === 1 ? "" : "s"})`
              : "Optimized route"
          }
          action={
            optimizeResult?.metrics ? (
              <span className="text-xs text-muted">
                {optimizeResult.metrics.distance_km} km · ~{optimizeResult.metrics.duration_minutes}{" "}
                min
              </span>
            ) : undefined
          }
          className="flex h-full flex-col"
        >
          {!optimizeResult ? (
            <div className="flex flex-1 flex-col items-center justify-center px-6 py-12 text-center">
              <Route className="mb-3 h-10 w-10 text-muted/40" />
              <p className="text-sm font-medium text-primary">No optimized route yet</p>
              <p className="mt-1 max-w-xs text-xs text-muted">
                Select parcels on the left, then click <strong>Optimize route</strong> to build the
                stop sequence here.
              </p>
            </div>
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-2 border-b border-primary/10 px-4 py-3">
                <span className="text-sm font-medium text-primary">
                  {optimizedSelected.length} stop{optimizedSelected.length === 1 ? "" : "s"} ·{" "}
                  {selectedOrderIds.length} parcel{selectedOrderIds.length === 1 ? "" : "s"}
                </span>
                <Select
                  value={batchDriverId}
                  onChange={(e) => setBatchDriverId(e.target.value)}
                  className="w-44"
                >
                  <option value="">Assign driver…</option>
                  {(driversList ?? []).map((d: AssignableDriver) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                      {d.online ? " ●" : ""}
                    </option>
                  ))}
                </Select>
                <Button
                  className="gap-2 px-3 py-1.5 text-xs"
                  onClick={() => void assignBatch()}
                  disabled={!batchDriverId || selectedOrderIds.length === 0 || assigning}
                >
                  <Users className="h-4 w-4" />
                  {assigning ? "Assigning…" : "Assign selected"}
                </Button>
              </div>

              {optimizeResult.warnings.length > 0 && (
                <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-900">
                  <p className="font-medium">Warnings</p>
                  <ul className="mt-1 list-inside list-disc">
                    {optimizeResult.warnings.map((w) => (
                      <li key={w}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="min-h-0 flex-1 overflow-y-auto">
                <label className="flex cursor-pointer items-center gap-3 border-b border-primary/5 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-muted">
                  <input
                    type="checkbox"
                    checked={allOptimizedSelected}
                    onChange={toggleAllOptimized}
                    className="h-4 w-4 rounded border-primary/20 text-secondary"
                  />
                  Select all stops
                </label>
                <div className="divide-y divide-primary/5">
                  {optimizedStops.map((s) => {
                    const key = stopKey(s);
                    const checked = optimizedSelected.includes(key);
                    return (
                      <label
                        key={key}
                        className={cn(
                          "flex cursor-pointer items-start gap-3 px-4 py-3 transition-colors hover:bg-primary/[0.02]",
                          checked && "bg-secondary/[0.05]"
                        )}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleOptimized(key)}
                          className="mt-0.5 h-4 w-4 shrink-0 rounded border-primary/20 text-secondary"
                        />
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-mono text-xs font-bold text-secondary">
                              #{s.sequence}
                            </span>
                            <Badge tone={s.type === "pickup" ? "blue" : "green"}>
                              {titleCase(s.type)}
                            </Badge>
                            <span className="font-mono text-xs font-semibold text-primary">
                              {s.tracking_number}
                            </span>
                          </div>
                          <p className="mt-0.5 truncate text-xs text-muted">{s.address ?? "—"}</p>
                          {s.leg_duration_seconds ? (
                            <p className="mt-0.5 text-[11px] text-muted">
                              Leg ~{Math.round(s.leg_duration_seconds / 60)} min
                            </p>
                          ) : null}
                        </div>
                      </label>
                    );
                  })}
                </div>
              </div>
            </>
          )}
        </SectionCard>
      </div>
    </div>
  );
}
