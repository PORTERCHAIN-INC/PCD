"use client";

import { ExceptionsPanel } from "@/components/operations/ExceptionsPanel";
import { SlaPanel } from "@/components/operations/SlaPanel";

/** Merged Exceptions + SLA for the Attention primary view. */
export function AttentionPanel({
  tick,
  onOpenOrder,
}: {
  tick: number;
  onOpenOrder: (id: string) => void;
}) {
  return (
    <div className="space-y-5">
      <ExceptionsPanel tick={tick} onOpenOrder={onOpenOrder} />
      <SlaPanel tick={tick} onOpenOrder={onOpenOrder} />
    </div>
  );
}
