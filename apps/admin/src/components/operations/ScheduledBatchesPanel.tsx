"use client";

import { useMemo, useState } from "react";
import { Package, Truck } from "lucide-react";
import { DateField } from "@porterchain/ui/date-fields";
import { useApiData } from "@/hooks/useApiData";
import { ops, type FleetbaseManifest, type ScheduledBatch } from "@/lib/operations";
import { Badge, EmptyState, SectionCard, Spinner } from "@/components/crm/primitives";
import { money, titleCase } from "@/lib/crmFormat";

function todayIso(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function BatchCard({
  batch,
  onOpenOrder,
}: {
  batch: ScheduledBatch;
  onOpenOrder: (id: string) => void;
}) {
  const [open, setOpen] = useState(true);
  return (
    <div className="rounded-2xl border border-primary/10 bg-white">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left"
      >
        <div>
          <p className="text-sm font-semibold text-primary">{batch.merchant_name ?? "Merchant"}</p>
          <p className="text-xs text-muted">
            {batch.pickup_address || "Pickup TBD"}
            {batch.pickup_window_start || batch.pickup_window_end
              ? ` · window ${batch.pickup_window_start?.slice(11, 16) ?? "?"}–${batch.pickup_window_end?.slice(11, 16) ?? "?"}`
              : null}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Badge tone="slate">{batch.order_count} orders</Badge>
          <span className="text-xs font-medium text-primary">{money(batch.amount_cents)}</span>
        </div>
      </button>
      {open && (
        <ul className="divide-y divide-primary/5 border-t border-primary/10">
          {batch.orders.map((o) => (
            <li key={o.id}>
              <button
                type="button"
                onClick={() => onOpenOrder(o.id)}
                className="flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left hover:bg-gray-bg"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-primary">{o.tracking_number}</p>
                  <p className="truncate text-xs text-muted">
                    {o.pickup || "—"} · {o.stop_count} stops
                  </p>
                </div>
                <Badge tone="slate">{titleCase(o.state)}</Badge>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ManifestRow({ m }: { m: FleetbaseManifest }) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-xl border border-primary/10 px-3 py-2.5">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-primary">
          {m.public_id || m.id || "Manifest"}
        </p>
        <p className="text-xs text-muted">
          {[m.driver_name, m.vehicle_name].filter(Boolean).join(" · ") || "Unassigned resources"}
          {m.stop_count != null ? ` · ${m.stop_count} stops` : ""}
        </p>
      </div>
      {m.status && <Badge tone="slate">{titleCase(m.status)}</Badge>}
    </div>
  );
}

export function ScheduledBatchesPanel({
  tick,
  onOpenOrder,
}: {
  tick: number;
  onOpenOrder: (id: string) => void;
}) {
  const [day, setDay] = useState(todayIso);
  const deps = useMemo(() => [tick, day], [tick, day]);

  const { data: batches, loading: batchesLoading } = useApiData(
    (t) => ops.scheduledBatches(t, day),
    deps,
    { key: `ops-batches-${day}` }
  );
  const { data: manifests, loading: manifestsLoading } = useApiData(
    (t) => ops.manifests(t, day),
    deps,
    { key: `ops-manifests-${day}` }
  );

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
      <SectionCard
        title={
          <span className="flex items-center gap-2">
            <Package className="h-4 w-4 text-secondary" /> Merchant pickup batches
          </span>
        }
        action={
          <div className="w-56">
            <DateField value={day} onChange={setDay} datePlaceholder="Pick a day" />
          </div>
        }
      >
        <div className="space-y-3 p-4">
          <p className="text-xs text-muted">
            Planning view — open scheduled pickups grouped by merchant for {day}. Commit via
            Fleetbase orchestrator creates vehicle manifests (right).
          </p>
          {batchesLoading && !batches ? (
            <Spinner />
          ) : !batches?.batches.length ? (
            <EmptyState
              title="No scheduled batches"
              hint="Create a scheduled pickup from New order, or book with schedule later."
            />
          ) : (
            <>
              <p className="text-xs font-medium text-primary">
                {batches.batch_count} merchant batch{batches.batch_count === 1 ? "" : "es"} ·{" "}
                {batches.order_count} order{batches.order_count === 1 ? "" : "s"}
              </p>
              <div className="space-y-3">
                {batches.batches.map((b) => (
                  <BatchCard
                    key={b.merchant_id ?? b.merchant_name ?? "x"}
                    batch={b}
                    onOpenOrder={onOpenOrder}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      </SectionCard>

      <SectionCard
        title={
          <span className="flex items-center gap-2">
            <Truck className="h-4 w-4 text-secondary" /> Fleetbase manifests
          </span>
        }
      >
        <div className="space-y-3 p-4">
          <p className="text-xs text-muted">
            Execution plans from ManifestController (per vehicle after orchestrator commit).
            {manifests?.source ? ` Source: ${manifests.source}.` : ""}
          </p>
          {manifestsLoading && !manifests ? (
            <Spinner />
          ) : !manifests?.manifests.length ? (
            <EmptyState
              title="No committed manifests"
              hint={
                manifests?.note ||
                "Empty until orchestrator commit, or when /int/v1 auth is unavailable."
              }
            />
          ) : (
            <div className="space-y-2">
              {manifests.manifests.map((m) => (
                <ManifestRow key={m.id || m.public_id || JSON.stringify(m)} m={m} />
              ))}
            </div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
