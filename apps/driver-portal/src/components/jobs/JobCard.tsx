import Link from "next/link";
import { ArrowRight, MapPin, Package } from "lucide-react";
import type { DriverJobSummary } from "@/lib/jobs";
import { jobStatusColor, jobStatusLabel, legLabel, urgencyColor, urgencyLabel } from "@/lib/jobs";
import { cn } from "@/lib/utils";

const BADGE: Record<string, string> = {
  emerald: "bg-emerald-100 text-emerald-800",
  amber: "bg-amber-100 text-amber-800",
  red: "bg-red-100 text-red-800",
  slate: "bg-slate-100 text-slate-700",
};

export function JobCard({
  job,
  highlight,
  onAccept,
  onReject,
  actionPending,
}: {
  job: DriverJobSummary;
  highlight?: boolean;
  onAccept?: (orderId: string) => void;
  onReject?: (orderId: string) => void;
  actionPending?: string | null;
}) {
  const color = jobStatusColor(job.state);
  const urgency = job.urgency ?? "normal";
  const needsAssignment = job.state === "DRIVER_ASSIGNED" && onAccept && onReject;
  const leg = job.current_leg ?? (job.pickup_completed ? "delivery" : "pickup");
  const isActive = job.is_current_job || highlight;
  return (
    <div
      className={cn(
        "block rounded-2xl border bg-white p-4 shadow-sm transition hover:shadow-md",
        isActive
          ? "border-[var(--secondary)] ring-2 ring-[var(--secondary)]/20"
          : "border-transparent"
      )}
    >
      {isActive && (
        <p className="mb-2 text-xs font-bold uppercase tracking-wide text-[var(--secondary)]">
          Active now
        </p>
      )}
      <Link href={`/jobs/${job.order_id}`} className="block">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            {job.priority_rank != null && (
              <span
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[var(--primary)] text-sm font-bold text-white"
                title="Route priority"
              >
                {job.priority_rank}
              </span>
            )}
            <div>
              <p className="font-bold text-[var(--primary)]">{job.order_number}</p>
              <p className="text-xs text-[var(--muted)]">{job.tracking_number}</p>
            </div>
          </div>
          <div className="flex flex-col items-end gap-1.5">
            <span className={cn("rounded-full px-2.5 py-1 text-xs font-semibold", BADGE[color])}>
              {jobStatusLabel(job.state)}
            </span>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-slate-700">
              {legLabel(leg === "completed" ? "completed" : leg)}
            </span>
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide",
                urgencyColor(urgency)
              )}
            >
              {urgencyLabel(urgency)}
            </span>
          </div>
        </div>
        <div className="mt-3 space-y-2 text-sm">
          <p className="flex items-start gap-2">
            <Package className="mt-0.5 h-4 w-4 shrink-0 text-blue-600" />
            <span className="text-[var(--muted)]">{job.pickup_address}</span>
          </p>
          <p className="flex items-start gap-2">
            <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
            <span>{job.delivery_address}</span>
          </p>
        </div>
        {job.special_instructions && (
          <p className="mt-2 line-clamp-2 text-xs text-amber-800 bg-amber-50 rounded-lg px-2 py-1">
            {job.special_instructions}
          </p>
        )}
        <p className="mt-3 flex items-center gap-1 text-xs font-semibold text-[var(--secondary)]">
          Open Delivery 360
          <ArrowRight className="h-3.5 w-3.5" />
        </p>
      </Link>
      {needsAssignment && (
        <div className="mt-3 flex gap-2 border-t border-[var(--gray-bg)] pt-3">
          <button
            type="button"
            disabled={actionPending === job.order_id}
            onClick={() => onAccept(job.order_id)}
            className="flex-1 rounded-xl bg-[var(--secondary)] py-2 text-xs font-bold text-white disabled:opacity-50"
          >
            Accept
          </button>
          <button
            type="button"
            disabled={actionPending === job.order_id}
            onClick={() => onReject(job.order_id)}
            className="flex-1 rounded-xl border border-[var(--primary)]/15 py-2 text-xs font-bold disabled:opacity-50"
          >
            Reject
          </button>
        </div>
      )}
    </div>
  );
}
