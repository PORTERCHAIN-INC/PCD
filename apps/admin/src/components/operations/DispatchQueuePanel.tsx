"use client";

import { useRef, useState, type ReactNode } from "react";
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
import { GripVertical, Sparkles, Truck } from "lucide-react";
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
import { formatSuggestionEta } from "@/lib/telemetryLabels";

const DESK_PANE =
  "flex min-h-[28rem] max-h-[min(70vh,40rem)] flex-col xl:min-h-[32rem] xl:max-h-[min(72vh,44rem)]";

function SlaBadge({ sla }: { sla: string }) {
  const tone = sla === "breached" ? "red" : sla === "at_risk" ? "amber" : "green";
  return <Badge tone={tone}>{titleCase(sla)}</Badge>;
}

type RankedSuggestions = { drivers: SuggestedDriver[]; source?: string };

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
  suggestions: RankedSuggestions | undefined;
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
            {suggestionsLoading || suggestions?.source === "pending"
              ? "Ranking…"
              : suggestions
                ? "Refresh"
                : "Suggest"}
          </Button>
        </div>
      </div>

      {(suggestionsLoading || suggestions?.source === "pending") && (
        <p className="mt-2 pl-6 text-xs text-muted">Ranking…</p>
      )}
      {suggestions && suggestions.source !== "pending" && !suggestionsLoading && (
        <div className="mt-2 flex flex-wrap items-center gap-2 pl-6">
          {suggestions.drivers.length === 0 && (
            <span className="text-xs text-muted">No approved drivers available.</span>
          )}
          {suggestions.drivers.slice(0, 3).map((d, rank) => (
            <button
              key={d.id}
              type="button"
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
                {formatSuggestionEta(d.eta_minutes, d.eta_source)} · load {d.active_orders}
              </span>
              {rank === 0 && <Badge tone="blue">Best</Badge>}
            </button>
          ))}
          {suggestions.drivers.length > 3 && (
            <span className="text-[11px] text-muted">
              +{suggestions.drivers.length - 3} more ranked
            </span>
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
        isOver
          ? "border-secondary bg-secondary/10 ring-2 ring-secondary/30"
          : "border-primary/10 bg-white"
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
  /** When set, desk becomes Queue | Map | Drivers (3-pane). */
  mapSlot?: ReactNode;
};

export function DispatchQueuePanel({ tick, onAssigned, onOpenOrder, mapSlot }: Props) {
  const { getApiToken } = useAdminAuth();
  const { data, loading, error, refetch, isFetching } = useApiData((t) => ops.queue(t), [tick], {
    key: "ops-queue",
  });
  const { data: driversList, loading: driversLoading } = useApiData(
    (t) => ops.assignableDrivers(t),
    [tick],
    { key: "ops-assignable-drivers" }
  );

  const [suggestions, setSuggestions] = useState<Record<string, RankedSuggestions>>({});
  const [suggesting, setSuggesting] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [activeOrder, setActiveOrder] = useState<QueueOrder | null>(null);
  const suppressClickUntil = useRef(0);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  const orders = data ?? [];
  const drivers = driversList ?? [];
  const onlineCount = drivers.filter((d) => d.is_online).length;

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
      let res = await ops.driverSuggestions(token, orderId);
      if (res.source === "pending") {
        setSuggestions((prev) => ({ ...prev, [orderId]: { drivers: [], source: "pending" } }));
        for (let i = 0; i < 10; i += 1) {
          await new Promise((r) => setTimeout(r, 1000));
          res = await ops.driverSuggestions(token, orderId);
          if (res.source !== "pending") break;
        }
      }
      setSuggestions((prev) => ({
        ...prev,
        [orderId]: { drivers: res.source === "pending" ? [] : res.drivers, source: res.source },
      }));
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
      <SectionCard title="Dispatch queue" className={DESK_PANE}>
        <Spinner label="Loading dispatch queue…" />
      </SectionCard>
    );
  }

  if (error) {
    return (
      <SectionCard title="Dispatch queue" className={DESK_PANE}>
        <div className="space-y-3 px-5 py-6 text-center">
          <p className="text-sm text-red-600">Could not load dispatch queue: {error}</p>
          <Button variant="outline" onClick={() => void refetch()} disabled={isFetching}>
            {isFetching ? "Retrying…" : "Retry"}
          </Button>
        </div>
      </SectionCard>
    );
  }

  const queuePane = (
    <SectionCard
      title={`Dispatch queue (${orders.length})`}
      action={
        <span className="text-xs text-muted">
          {driversLoading ? "…" : `${onlineCount} online · ${drivers.length} approved`}
        </span>
      }
      className={DESK_PANE}
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
  );

  const driversPane = (
    <SectionCard
      title="Drivers"
      icon={<Truck className="h-4 w-4 text-secondary" />}
      action={<span className="text-xs text-muted">drop to assign</span>}
      className={DESK_PANE}
    >
      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto px-3 py-3">
        {driversLoading && drivers.length === 0 ? (
          <Spinner label="Loading drivers…" />
        ) : drivers.length === 0 ? (
          <EmptyState title="No approved drivers" hint="Approve drivers to dispatch work." />
        ) : (
          <>
            {drivers.filter((d) => d.is_online).length > 0 && (
              <p className="px-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted">
                Online
              </p>
            )}
            {drivers
              .filter((d) => d.is_online)
              .map((d) => (
                <DriverCard key={d.id} d={d} />
              ))}
            {drivers.some((d) => !d.is_online) && (
              <p className="px-0.5 pt-2 text-[10px] font-semibold uppercase tracking-wide text-muted">
                Offline
              </p>
            )}
            {drivers
              .filter((d) => !d.is_online)
              .map((d) => (
                <DriverCard key={d.id} d={d} />
              ))}
          </>
        )}
      </div>
    </SectionCard>
  );

  const gridClass = mapSlot
    ? "grid gap-3 xl:grid-cols-[minmax(16rem,0.9fr)_minmax(0,1.5fr)_minmax(13rem,0.7fr)] xl:items-stretch"
    : "grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(13rem,18rem)] lg:items-stretch";

  return (
    <DndContext sensors={sensors} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
      <div className="space-y-3">
        {actionError && (
          <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
            {actionError}
          </p>
        )}

        <div className={gridClass}>
          {queuePane}
          {mapSlot ? (
            <div className={cn(DESK_PANE, "ops-desk-map-fill min-w-0")}>{mapSlot}</div>
          ) : null}
          {driversPane}
        </div>

        <p className="px-1 text-xs text-muted">
          Drag an order onto a driver, or use Suggest for ETA/load-ranked matches. Live map
          positions come from Fleetbase via the adapter. Batch optimize lives under Tools →
          Optimize.
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
