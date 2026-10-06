"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { PageSkeleton } from "@porterchain/ui/loading";
import DriverShell from "@/components/DriverShell";
import { useJobDetail } from "@/hooks/useJobDetail";

const Delivery360 = dynamic(() => import("@/components/jobs/Delivery360"), {
  loading: () => <PageSkeleton rows={4} />,
});

export default function JobDetailClient({ orderId }: { orderId: string }) {
  const { job, error, loading, lastUpdatedLabel, refresh } = useJobDetail(orderId);

  return (
    <DriverShell>
      <div className="mb-6 flex items-center justify-between gap-4">
        <Link
          href="/jobs"
          className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--secondary)] hover:underline"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Jobs
        </Link>
        {lastUpdatedLabel && (
          <p className="text-xs text-[var(--muted)]">
            Live · {lastUpdatedLabel}
            <button
              type="button"
              onClick={() => void refresh()}
              className="ml-2 font-semibold text-[var(--secondary)]"
            >
              Refresh
            </button>
          </p>
        )}
      </div>

      {loading && !job && <PageSkeleton rows={4} />}
      {error && <p className="text-red-600">{error}</p>}
      {job && <Delivery360 job={job} routeId={job.route_id} onUpdated={() => void refresh()} />}
    </DriverShell>
  );
}
