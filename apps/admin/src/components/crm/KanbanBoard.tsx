"use client";

import { useEffect, useMemo, useState } from "react";
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
import { Building2, GripVertical, MapPin, Sparkles, UserPlus } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import type { PipelineCard, PipelineColumn } from "@/lib/crm";
import { STAGE_ACCENT, STAGE_LABELS, money } from "@/lib/crmFormat";

function Card({ card, dragging }: { card: PipelineCard; dragging?: boolean }) {
  const isLead = card.type === "lead";
  return (
    <div
      className={cn(
        "group rounded-xl border bg-white p-3 shadow-sm transition-shadow",
        isLead ? "border-l-4 border-l-amber-400 border-primary/10" : "border-primary/10",
        dragging ? "rotate-1 shadow-lg" : "hover:shadow-md"
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-semibold leading-snug text-primary">{card.title}</p>
        <GripVertical className="h-4 w-4 shrink-0 text-muted opacity-0 group-hover:opacity-100" />
      </div>
      {card.company_name && (
        <p className="mt-1 flex items-center gap-1 text-xs text-muted">
          {isLead ? <MapPin className="h-3 w-3" /> : <Building2 className="h-3 w-3" />}
          {card.company_name}
        </p>
      )}
      <div className="mt-3 flex items-center justify-between">
        <span className="text-sm font-bold text-secondary">{money(card.value_cents)}</span>
        {isLead ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
            <Sparkles className="h-3 w-3" />
            {card.score ?? 0}
          </span>
        ) : (
          <span className="rounded-full bg-gray-bg px-2 py-0.5 text-xs font-medium text-primary/70">
            {card.probability}%
          </span>
        )}
      </div>
    </div>
  );
}

function DraggableCard({ card, onClick }: { card: PipelineCard; onClick: () => void }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: card.id,
    data: { card },
  });
  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      onClick={onClick}
      className={cn("touch-none", isDragging && "opacity-30")}
    >
      <Card card={card} />
    </div>
  );
}

function Column({
  column,
  onCardClick,
}: {
  column: PipelineColumn;
  onCardClick: (card: PipelineCard) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: column.stage });
  const accent = STAGE_ACCENT[column.stage] ?? "#64748b";
  return (
    <div className="flex w-72 shrink-0 flex-col">
      <div className="mb-2 flex items-center justify-between px-1">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full" style={{ background: accent }} />
          <span className="text-sm font-semibold text-primary">
            {STAGE_LABELS[column.stage] ?? column.stage}
          </span>
          <span className="rounded-full bg-gray-bg px-1.5 text-xs text-muted">{column.count}</span>
        </div>
        <span className="text-xs font-medium text-muted">{money(column.value_cents)}</span>
      </div>
      {(column.lead_count > 0 || column.deal_count > 0) && (
        <div className="mb-2 flex gap-2 px-1 text-[11px] text-muted">
          {column.lead_count > 0 && (
            <span className="inline-flex items-center gap-1">
              <UserPlus className="h-3 w-3 text-amber-500" />
              {column.lead_count} leads
            </span>
          )}
          {column.deal_count > 0 && <span>· {column.deal_count} deals</span>}
        </div>
      )}
      <div
        ref={setNodeRef}
        className={cn(
          "flex min-h-[60vh] flex-col gap-2 rounded-2xl border border-dashed p-2 transition-colors",
          isOver ? "border-secondary bg-secondary/5" : "border-primary/10 bg-gray-bg/40"
        )}
      >
        {column.cards.map((card) => (
          <DraggableCard key={card.id} card={card} onClick={() => onCardClick(card)} />
        ))}
        {column.hidden > 0 && (
          <p className="rounded-lg bg-white/60 px-2 py-2 text-center text-xs text-muted">
            +{column.hidden.toLocaleString()} more leads — use Leads filters to refine
          </p>
        )}
        {column.cards.length === 0 && column.hidden === 0 && (
          <p className="px-2 py-6 text-center text-xs text-muted">Drop here</p>
        )}
      </div>
    </div>
  );
}

export function KanbanBoard({
  columns,
  onMove,
  onCardClick,
}: {
  columns: PipelineColumn[];
  onMove: (card: PipelineCard, toStage: string, position: number) => void;
  onCardClick: (card: PipelineCard) => void;
}) {
  const [local, setLocal] = useState<PipelineColumn[]>(columns);
  const [active, setActive] = useState<PipelineCard | null>(null);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  // eslint-disable-next-line react-hooks/set-state-in-effect -- resync local drag state when the source columns change
  useEffect(() => setLocal(columns), [columns]);

  const findCard = useMemo(
    () => (id: string) => local.flatMap((c) => c.cards).find((card) => card.id === id) ?? null,
    [local]
  );

  function handleStart(event: DragStartEvent) {
    setActive(
      (event.active.data.current?.card as PipelineCard) ?? findCard(String(event.active.id))
    );
  }

  function handleEnd(event: DragEndEvent) {
    setActive(null);
    const { active: a, over } = event;
    if (!over) return;
    const card = (a.data.current?.card as PipelineCard) ?? findCard(String(a.id));
    const toStage = String(over.id);
    if (!card || card.stage === toStage) return;

    setLocal((prev) =>
      prev.map((col) => {
        if (col.stage === card.stage) {
          const cards = col.cards.filter((x) => x.id !== card.id);
          return { ...col, cards, count: Math.max(0, col.count - 1) };
        }
        if (col.stage === toStage) {
          return {
            ...col,
            cards: [...col.cards, { ...card, stage: toStage }],
            count: col.count + 1,
          };
        }
        return col;
      })
    );
    const target = local.find((c) => c.stage === toStage);
    onMove(card, toStage, target ? target.cards.length : 0);
  }

  return (
    <DndContext sensors={sensors} onDragStart={handleStart} onDragEnd={handleEnd}>
      <div className="flex gap-4 overflow-x-auto pb-4">
        {local.map((column) => (
          <Column key={column.stage} column={column} onCardClick={onCardClick} />
        ))}
      </div>
      <DragOverlay>{active ? <Card card={active} dragging /> : null}</DragOverlay>
    </DndContext>
  );
}
