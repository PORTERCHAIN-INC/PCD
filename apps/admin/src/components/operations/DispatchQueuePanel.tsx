"use client";

import { useRef, useState } from "react";
import {
  DndContext,
  type DragEndEvent,
  type DragStartEvent,
  DragOverlay,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { GripVertical, Sparkles } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { api } from "@/lib/api";
import {
  ops,
  type AssignableDriver,
  type QueueOrder,
  type SuggestedDriver,
} from "@/lib/operations";
import { Badge, Button, EmptyState, SectionCard, Spinner } from "@/components/crm/primitives";
import { titleCase } from "@/lib/crmFormat";

function SlaBadge({ sla }: { sla: string }) {
  const tone = sla === "breached" ? "red" : sla === "at_risk" ? "amber" : "green";
  return <Badge tone={tone}>{titleCase(sla)}</Badge>;
}

function QueueRow({
  o,
  suggestions,
  suggestionsLoading,
  onSuggest,
  onPickSuggestion,
  onOpenOrder,
  suppressClickUntil,
  busy,
}: {
  o: QueueOrder;
  suggestions: SuggestedDriver[] | undefined;
  suggestionsLoading: boolean;
  onSuggest: (orderId: string) => void;
  onPickSuggestion: (orderId: string, driverId: string) => void;
  onOpenOrder?: (orderId: string) => void;
  suppressClickUntil: React.RefObject<number>;
  busy: boolean;
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: o.id,
    data: { order: o },
  });
  const missingCoords =
    o.stop_phase === "delivery_only"
      ? !o.has_dropoff_coords
      : !o.has_pickup_coords || !o.has_dropoff_coords;

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      className={cn(
        "touch-none px-4 py-3",
        isDragging ? "opacity-30" : "cursor-grab active:cursor-grabbing"
      )}
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div
          className={cn(
            "-mx-2 -my-1 min-w-0 flex-1 rounded-lg px-2 py-1",
            onOpenOrder && "cursor-pointer transition-colors hover:bg-gray-bg/70"
          )}
          onClick={() => {
            if (Date.now() < (suppressClickUntil.current ?? 0)) return;
            onOpenOrder?.(o.id);
          }}
          title={onOpenOrder ? "Open Order 360 · drag row onto a driver to assign" : undefined}
        >
          <p className="flex flex-wrap items-center gap-2 font-mono text-xs font-semibold text-primary">
            <GripVertical className="h-3.5 w-3.5 text-muted" />
            <span>{o.tracking_number}</span>
            {o.high_priority ? <Badge tone="red">High</Badge> : null}
            <Badge tone="slate">{titleCase(o.state)}</Badge>
            {missingCoords ? <Badge tone="amber">Missing coords</Badge> : null}
          </p>
          <p className="truncate text-xs text-muted">
            {o.merchant ?? "—"} · {o.pickup ?? "?"} → {o.dropoff ?? "?"}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <SlaBadge sla={o.sla} />
          <Button
            variant="outline"
            className="shrink-0 px-3 py-1.5 text-xs"
            onClick={() => onSuggest(o.id)}
            disabled={suggestionsLoading}
          >
            <Sparkles className="h-3.5 w-3.5" />
            {suggestionsLoading ? "Ranking…" : suggestions ? "Refresh" : "Suggest"}
          </Button>
        </div>
      </div>

      {suggestions && (
        <div className="mt-2 flex flex-wrap items-center gap-2 pl-6">
          {suggestions.length === 0 && (
            <span className="text-xs text-muted">No approved drivers available.</span>
          )}
          {suggestions.slice(0, 3).map((d, rank) => (
            <button
              key={d.id}
              onClick={() => onPickSuggestion(o.id, d.id)}
              disabled={busy}
              title={d.reasons.join(" · ")}
              className={cn(
                "flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors disabled:opacity-50",
                rank === 0
                  ? "border-secondary/40 bg-secondary/10 text-secondary hover:bg-secondary/20"
                  : "border-primary/15 bg-white text-primary hover:bg-gray-bg"
              )}
            >
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  d.online ? "bg-green-500" : "bg-gray-300"
                )}
              />
              {d.name}
              <span className="text-muted">
                {d.eta_minutes != null ? `${Math.round(d.eta_minutes)}m` : "—"} · load{" "}
                {d.active_orders}
              </span>
              {rank === 0 && <Badge tone="blue">Best</Badge>}
            </button>
          ))}
          {suggestions.length > 3 && (
            <span className="text-[11px] text-muted">+{suggestions.length - 3} more ranked</span>
          )}
        </div>
      )}
    </div>
  );
}

function DriverCard({ d }: { d: AssignableDriver }) {
  const { setNodeRef, isOver } = useDroppable({ id: d.id, data: { driver: d } });
  return (
    <div
      ref={setNodeRef}
      className={cn(
        "rounded-xl border p-3 transition-colors",
        isOver ? "border-secondary bg-secondary/10" : "border-primary/10 bg-white"
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <p className="flex min-w-0 items-center gap-2 text-sm font-medium text-primary">
          <span
            className={cn(
              "h-2 w-2 shrink-0 rounded-full",
              d.is_online ? "bg-green-500" : "bg-gray-300"
            )}
            title={d.is_online ? "Online (mirrored)" : "Offline"}
          />
          <span className="truncate">{d.name}</span>
        </p>
        <span className="shrink-0 text-xs text-muted">
          {d.rating ? `${d.rating.toFixed(1)}★` : "—"}
        </span>
      </div>
      <p className="mt-1 text-xs text-muted">
        {(d.active_orders ?? 0) === 0
          ? "No active load"
          : `${d.active_orders} active delivery(ies)`}
      </p>
    </div>
  );
}

type Props = {
  tick: number;
  onAssigned: () => void;
  onOpenOrder?: (orderId: string) => void;
};

export function DispatchQueuePanel({ tick, onAssigned, onOpenOrder }: Props) {
  const { getApiToken } = useAdminAuth();
  const { data, loading, error, refetch, isFetching } = useApiData((t) => ops.queue(t), [tick], {
    key: "ops-queue",
  });
  const { data: driversList, loading: driversLoading } = useApiData(
    (t) => ops.assignableDrivers(t),
    [tick],
    { key: "ops-assignable-drivers" }
  );

  const [suggestions, setSuggestions] = useState<Record<string, SuggestedDriver[]>>({});
  const [suggesting, setSuggesting] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [activeOrder, setActiveOrder] = useState<QueueOrder | null>(null);
  const suppressClickUntil = useRef(0);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  const orders = data ?? [];
  const drivers = driversList ?? [];

  async function assign(orderId: string, driverId: string) {
    setBusy(orderId);
    setActionError(null);
    try {
      const token = await getApiToken();
      await api.assignDriver(token, orderId, driverId);
      setSuggestions((prev) => {
        const next = { ...prev };
        delete next[orderId];
        return next;
      });
      onAssigned();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Assign failed");
    } finally {
      setBusy(null);
    }
  }

  async function loadSuggestions(orderId: string) {
    setSuggesting(orderId);
    setActionError(null);
    try {
      const token = await getApiToken();
      const res = await ops.driverSuggestions(token, orderId);
      setSuggestions((prev) => ({ ...prev, [orderId]: res.drivers }));
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Could not rank drivers");
    } finally {
      setSuggesting(null);
    }
  }

  function handleDragStart(event: DragStartEvent) {
    setActiveOrder((event.active.data.current?.order as QueueOrder) ?? null);
  }

  function handleDragEnd(event: DragEndEvent) {
    suppressClickUntil.current = Date.now() + 250;
    const order = event.active.data.current?.order as QueueOrder | undefined;
    const driver = event.over?.data.current?.driver as AssignableDriver | undefined;
    setActiveOrder(null);
    if (!order || !driver) return;
    void assign(order.id, driver.id);
  }

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
    <DndContext sensors={sensors} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
      <div className="space-y-3">
        {actionError && (
          <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
            {actionError}
          </p>
        )}

        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_300px]">
          <SectionCard
            title={`Dispatch queue (${orders.length})`}
            action={
              <span className="text-xs text-muted">
                {driversLoading ? "Loading drivers…" : `${drivers.length} approved`}
              </span>
            }
            className="flex h-full flex-col"
          >
            <div className="min-h-0 flex-1 overflow-y-auto">
              {orders.length === 0 ? (
                <EmptyState title="Queue is clear" hint="No unassigned orders awaiting dispatch." />
              ) : (
                <div className="divide-y divide-primary/5">
                  {orders.map((o: QueueOrder) => (
                    <QueueRow
                      key={o.id}
                      o={o}
                      suggestions={suggestions[o.id]}
                      suggestionsLoading={suggesting === o.id}
                      onSuggest={(id) => void loadSuggestions(id)}
                      onPickSuggestion={(orderId, driverId) => void assign(orderId, driverId)}
                      onOpenOrder={onOpenOrder}
                      suppressClickUntil={suppressClickUntil}
                      busy={busy === o.id}
                    />
                  ))}
                </div>
              )}
            </div>
          </SectionCard>

          <SectionCard
            title="Drivers"
            action={<span className="text-xs text-muted">drop to assign</span>}
            className="flex h-full flex-col"
          >
            <div className="min-h-0 flex-1 space-y-2 overflow-y-auto px-3 py-3">
              {drivers.length === 0 ? (
                <EmptyState title="No approved drivers" hint="Approve drivers to dispatch work." />
              ) : (
                drivers.map((d) => <DriverCard key={d.id} d={d} />)
              )}
            </div>
          </SectionCard>
        </div>

        <p className="px-1 text-xs text-muted">
          Drag an order onto a driver, or use Suggest for ETA/load-ranked matches (live positions
          via Fleetbase when available). Batch optimize and multi-stop sequencing run in the
          Fleetbase console.
        </p>
      </div>

      <DragOverlay>
        {activeOrder ? (
          <div className="w-72 rotate-1 rounded-xl border border-primary/10 bg-white p-3 shadow-lg">
            <p className="font-mono text-xs font-semibold text-primary">
              {activeOrder.tracking_number}
            </p>
            <p className="mt-1 truncate text-xs text-muted">
              {activeOrder.pickup ?? "?"} → {activeOrder.dropoff ?? "?"}
            </p>
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}
