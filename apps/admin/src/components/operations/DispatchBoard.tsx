"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  type DragEndEvent,
  DragOverlay,
  type DragStartEvent,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { GripVertical } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { Badge } from "@/components/crm/primitives";
import {
  BOARD_ACCENT,
  BOARD_LABELS,
  SLA_TONE,
  type BoardColumn,
  type OpsOrder,
} from "@/lib/operations";
import { titleCase } from "@/lib/crmFormat";

const STATE_TONE = (sla: string) => SLA_TONE[sla] ?? "slate";

function SlaCountdown({ o }: { o: OpsOrder }) {
  const mins = o.sla_minutes_remaining;
  if (mins == null) {
    return (
      <Badge tone={STATE_TONE(o.sla)}>{o.sla === "at_risk" ? "At risk" : titleCase(o.sla)}</Badge>
    );
  }
  if (mins < 0) {
    const late = Math.abs(mins);
    const label = late >= 60 ? `${Math.floor(late / 60)}h late` : `${late}m late`;
    return <Badge tone="red">{label}</Badge>;
  }
  if (mins <= 30 || o.sla === "at_risk") {
    return <Badge tone="amber">{mins}m left</Badge>;
  }
  const label = mins >= 60 ? `${Math.floor(mins / 60)}h ${mins % 60}m` : `${mins}m left`;
  return <Badge tone="green">{label}</Badge>;
}

function WaypointChips({ o }: { o: OpsOrder }) {
  const total = o.stop_count ?? 2;
  const done = Math.min(o.stops_done ?? 0, total);
  return (
    <div className="mt-1.5 flex items-center gap-1" title={`${done}/${total} stops`}>
      {Array.from({ length: total }, (_, i) => (
        <span
          key={i}
          className={cn(
            "h-1.5 flex-1 rounded-full",
            i < done ? "bg-green-500" : i === done ? "bg-secondary" : "bg-primary/10"
          )}
        />
      ))}
      <span className="ml-1 shrink-0 text-[10px] tabular-nums text-muted">
        {done}/{total}
      </span>
    </div>
  );
}

function OrderCard({ o, dragging }: { o: OpsOrder; dragging?: boolean }) {
  return (
    <div
      className={cn(
        "group rounded-xl border border-primary/10 bg-white p-3 shadow-sm transition-shadow",
        dragging ? "rotate-1 shadow-lg" : "hover:shadow-md"
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="font-mono text-xs font-semibold text-primary">{o.tracking_number}</span>
        <div className="flex items-center gap-1">
          {o.high_priority && <Badge tone="red">High</Badge>}
          <GripVertical className="h-4 w-4 shrink-0 text-muted opacity-0 group-hover:opacity-100" />
        </div>
      </div>
      <p className="mt-1 truncate text-xs text-muted">{o.merchant ?? "—"}</p>
      <p className="mt-1 truncate text-xs text-primary">
        {o.pickup ?? "?"} → {o.dropoff ?? "?"}
      </p>
      <WaypointChips o={o} />
      <div className="mt-2 flex items-center justify-between gap-2">
        <span className="truncate text-xs text-muted">{o.driver ?? "Unassigned"}</span>
        <SlaCountdown o={o} />
      </div>
    </div>
  );
}

function DraggableOrderCard({
  order,
  onOpenOrder,
  suppressClickUntil,
}: {
  order: OpsOrder;
  onOpenOrder?: (order: OpsOrder) => void;
  suppressClickUntil: React.RefObject<number>;
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: order.id,
    data: { order },
  });
  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      onClick={() => {
        // Ignore the click that dnd-kit lets through right after a drag ends
        if (Date.now() < (suppressClickUntil.current ?? 0)) return;
        onOpenOrder?.(order);
      }}
      title="Click for Order 360 · drag to move"
      className={cn("touch-none cursor-grab active:cursor-grabbing", isDragging && "opacity-30")}
    >
      <OrderCard o={order} />
    </div>
  );
}

function BoardColumnView({
  column,
  onOpenOrder,
  suppressClickUntil,
}: {
  column: BoardColumn;
  onOpenOrder?: (order: OpsOrder) => void;
  suppressClickUntil: React.RefObject<number>;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: column.key });
  return (
    <div className="flex w-64 shrink-0 flex-col">
      <div className="mb-2 flex items-center justify-between px-1">
        <div className="flex items-center gap-2">
          <span
            className="h-2.5 w-2.5 rounded-full"
            style={{ background: BOARD_ACCENT[column.key] }}
          />
          <span className="text-sm font-semibold text-primary">
            {BOARD_LABELS[column.key] ?? column.key}
          </span>
          <span className="rounded-full bg-gray-bg px-1.5 text-xs text-muted">{column.count}</span>
        </div>
      </div>
      <div
        ref={setNodeRef}
        className={cn(
          "flex min-h-[50vh] flex-col gap-2 rounded-2xl border border-dashed p-2 transition-colors",
          isOver ? "border-secondary bg-secondary/5" : "border-primary/10 bg-gray-bg/40"
        )}
      >
        {column.orders.map((o) => (
          <DraggableOrderCard
            key={o.id}
            order={o}
            onOpenOrder={onOpenOrder}
            suppressClickUntil={suppressClickUntil}
          />
        ))}
        {column.hidden > 0 && (
          <p className="rounded-lg bg-white/60 px-2 py-2 text-center text-xs text-muted">
            +{column.hidden} more
          </p>
        )}
        {column.orders.length === 0 && (
          <p className="px-2 py-6 text-center text-xs text-muted">Drop here</p>
        )}
      </div>
    </div>
  );
}

/** Columns that open a confirm modal instead of optimistic board move. */
const CONFIRM_COLUMNS = new Set([
  "assigned",
  "failed",
  "returned",
  "lost",
  "damaged",
  "waiting_dispatch",
  "accepted",
  "heading_to_pickup",
  "at_pickup",
  "picked_up",
  "in_transit",
  "near_delivery",
  "delivered",
]);

export function DispatchBoard({
  columns,
  onMove,
  onRequestMove,
  onOpenOrder,
}: {
  columns: BoardColumn[];
  onMove: (order: OpsOrder, toColumn: string) => Promise<void>;
  /** When set, used for assign/exception/execution drops (no optimistic jump). */
  onRequestMove?: (order: OpsOrder, toColumn: string) => void;
  onOpenOrder?: (order: OpsOrder) => void;
}) {
  const [local, setLocal] = useState<BoardColumn[]>(columns);
  const [active, setActive] = useState<OpsOrder | null>(null);
  const suppressClickUntil = useRef(0);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  useEffect(() => setLocal(columns), [columns]);

  const findOrder = useMemo(
    () => (id: string) => local.flatMap((c) => c.orders).find((o) => o.id === id) ?? null,
    [local]
  );

  const columnForOrder = (order: OpsOrder) =>
    local.find((col) => col.orders.some((o) => o.id === order.id))?.key ?? null;

  function handleStart(event: DragStartEvent) {
    setActive((event.active.data.current?.order as OpsOrder) ?? findOrder(String(event.active.id)));
  }

  async function handleEnd(event: DragEndEvent) {
    setActive(null);
    suppressClickUntil.current = Date.now() + 250;
    const { active: a, over } = event;
    if (!over) return;

    const order = (a.data.current?.order as OpsOrder) ?? findOrder(String(a.id));
    const toColumn = String(over.id);
    const fromColumn = order ? columnForOrder(order) : null;
    if (!order || !fromColumn || fromColumn === toColumn) return;

    if (onRequestMove && CONFIRM_COLUMNS.has(toColumn)) {
      onRequestMove(order, toColumn);
      return;
    }

    const previous = local;
    setLocal((prev) =>
      prev.map((col) => {
        if (col.key === fromColumn) {
          const orders = col.orders.filter((x) => x.id !== order.id);
          return { ...col, orders, count: Math.max(0, col.count - 1) };
        }
        if (col.key === toColumn) {
          return { ...col, orders: [...col.orders, order], count: col.count + 1 };
        }
        return col;
      })
    );

    try {
      await onMove(order, toColumn);
    } catch {
      setLocal(previous);
    }
  }

  return (
    <DndContext sensors={sensors} onDragStart={handleStart} onDragEnd={handleEnd}>
      <div className="flex gap-3 overflow-x-auto pb-3">
        {local.map((column) => (
          <BoardColumnView
            key={column.key}
            column={column}
            onOpenOrder={onOpenOrder}
            suppressClickUntil={suppressClickUntil}
          />
        ))}
      </div>
      <DragOverlay>{active ? <OrderCard o={active} dragging /> : null}</DragOverlay>
    </DndContext>
  );
}
