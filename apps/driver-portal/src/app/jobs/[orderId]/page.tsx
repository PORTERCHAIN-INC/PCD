"use client";

import { useEffect } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import DriverShell from "@/components/DriverShell";
import { useJobDetail } from "@/hooks/useJobDetail";
import { hasDriverSession } from "@/lib/api";

const Delivery360 = dynamic(() => import("@/components/jobs/Delivery360"), {
  loading: () => <p className="text-[var(--muted)]">Loading job workspace…</p>,
});

export default function JobDetailPage() {
  const router = useRouter();
  const params = useParams();
  const orderId = String(params.orderId);
  const { job, error, loading, lastUpdatedLabel, refresh } = useJobDetail(orderId);

  useEffect(() => {
    hasDriverSession().then((ok) => {
      if (!ok) router.replace("/login");
    });
  }, [router]);

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
              onClick={refresh}
              className="ml-2 font-semibold text-[var(--secondary)]"
            >
              Refresh
            </button>
          </p>
        )}
      </div>

      {loading && !job && <p className="text-[var(--muted)]">Loading job…</p>}
      {error && <p className="text-red-600">{error}</p>}
      {job && <Delivery360 job={job} routeId={job.route_id} onUpdated={refresh} />}
    </DriverShell>
  );
}
