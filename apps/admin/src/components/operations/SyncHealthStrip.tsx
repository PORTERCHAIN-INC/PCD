"use client";

import Link from "next/link";
import { AlertTriangle, CheckCircle2, RefreshCw } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useApiData } from "@/hooks/useApiData";
import { ops } from "@/lib/operations";

/** Dispatch health strip for Operations Control Tower. */
export function SyncHealthStrip({
  tick = 0,
  compactWhenOk = true,
}: {
  tick?: number;
  compactWhenOk?: boolean;
}) {
  const { data, error } = useApiData((t) => ops.syncHealth(t), [tick], {
    key: "ops-sync-health",
  });

  if (error && !data) {
    return (
      <div
        className="flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50/50 px-3 py-2 text-xs text-amber-900"
        data-testid="ops-sync-health"
      >
        <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
        Dispatch health unavailable
      </div>
    );
  }
  if (!data?.queue) return null;

  const dead = data.dead_letters?.length ?? 0;
  const pending = Number(data.queue.pending ?? data.queue.queued ?? 0);
  const failed = Number(data.queue.failed ?? data.queue.dead ?? 0) || dead;
  const processing = Number(data.queue.processing ?? data.queue.inflight ?? 0);
  const healthy = dead === 0 && failed === 0 && pending + processing < 20;
  const tone = healthy
    ? {
        ring: "border-green-200 bg-green-50/50",
        label: "text-green-800",
        icon: "text-green-600",
      }
    : dead > 0 || failed > 0
      ? {
          ring: "border-red-200 bg-red-50/60",
          label: "text-red-900",
          icon: "text-red-600",
        }
      : {
          ring: "border-amber-200 bg-amber-50/60",
          label: "text-amber-900",
          icon: "text-amber-600",
        };
  const StatusIcon = healthy ? CheckCircle2 : dead > 0 ? AlertTriangle : RefreshCw;

  if (compactWhenOk && healthy) {
    return (
      <Link
        href="/system"
        data-testid="ops-sync-health"
        className={cn(
          "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[11px] font-medium",
          tone.ring,
          tone.label
        )}
        title="Dispatch is PorterChain — open System"
      >
        <StatusIcon className={cn("h-3.5 w-3.5", tone.icon)} />
        Dispatch ok
      </Link>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border px-3 py-2 text-xs",
        tone.ring
      )}
      data-testid="ops-sync-health"
    >
      <span className={cn("flex items-center gap-1.5 font-semibold", tone.label)}>
        <StatusIcon className={cn("h-3.5 w-3.5", tone.icon)} />
        Dispatch
      </span>
      <span className="text-primary/80">
        Queue pending {pending}
        {processing > 0 ? ` · processing ${processing}` : ""}
      </span>
      {dead > 0 && <span className="font-medium text-red-700">{dead} dead letter(s)</span>}
      {failed > 0 && dead === 0 && (
        <span className="font-medium text-red-700">{failed} failed</span>
      )}
      <Link href="/system" className="font-medium text-secondary hover:underline">
        System →
      </Link>
    </div>
  );
}
