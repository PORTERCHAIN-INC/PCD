"use client";

import { AlertTriangle } from "lucide-react";
import { DispatchQueuePanel } from "@/components/operations/DispatchQueuePanel";
import { LiveMapPanel } from "@/components/operations/LiveMapPanel";
import { ActivityPanel } from "@/components/operations/ActivityPanel";
import { Button } from "@/components/crm/primitives";
import { pressureCounts } from "@/components/operations/opsViews";
import type { OpsStats } from "@/lib/operations";

export function OpsDeskLayout({
  tick,
  stats,
  onAssigned,
  onOpenOrder,
  onOpenAttention,
}: {
  tick: number;
  stats: OpsStats | null | undefined;
  onAssigned: () => void;
  onOpenOrder: (id: string) => void;
  onOpenAttention: () => void;
}) {
  const pressure = pressureCounts(stats);

  return (
    <div className="space-y-3">
      {pressure.hasPressure && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-200 bg-amber-50/60 px-4 py-2 text-sm text-amber-950">
          <span className="flex items-center gap-2 font-medium">
            <AlertTriangle className="h-4 w-4 text-amber-600" />
            Attention
            {pressure.waiting > 0 && (
              <span className="text-xs font-normal text-amber-800">
                · {pressure.waiting} waiting
              </span>
            )}
            {pressure.exceptions > 0 && (
              <span className="text-xs font-normal text-amber-800">
                · {pressure.exceptions} exceptions
              </span>
            )}
            {pressure.sla > 0 && (
              <span className="text-xs font-normal text-amber-800">· {pressure.sla} SLA</span>
            )}
            {pressure.delayed > 0 && (
              <span className="text-xs font-normal text-amber-800">
                · {pressure.delayed} delayed
              </span>
            )}
          </span>
          <Button variant="outline" className="text-xs" onClick={onOpenAttention}>
            Open Attention
          </Button>
        </div>
      )}

      {/* Three-pane desk: Queue | Map | Drivers — map is the spatial anchor */}
      <DispatchQueuePanel
        tick={tick}
        onAssigned={onAssigned}
        onOpenOrder={onOpenOrder}
        mapSlot={<LiveMapPanel tick={tick} onOpenOrder={onOpenOrder} embedded />}
      />

      <ActivityPanel tick={tick} compact onOpenOrder={onOpenOrder} />
    </div>
  );
}
