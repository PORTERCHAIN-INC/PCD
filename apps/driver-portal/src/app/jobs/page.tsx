"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Briefcase, CheckCircle2, Clock, History, Route } from "lucide-react";
import DriverShell from "@/components/DriverShell";
import { JobCard } from "@/components/jobs/JobCard";
import { useDriverJobs } from "@/hooks/useDriverJobs";
import { driverApi, hasDriverSession } from "@/lib/api";
import { cn } from "@/lib/utils";

type Tab = "all" | "current" | "upcoming" | "completed" | "history";

export default function JobsPage() {
  const router = useRouter();
  const { data, history, error, loading, optimizing, optimizeMessage, lastUpdatedLabel, refresh, optimize } =
    useDriverJobs();
  const [tab, setTab] = useState<Tab>("all");
  const [tabInitialized, setTabInitialized] = useState(false);
  const [assignPending, setAssignPending] = useState<string | null>(null);

  useEffect(() => {
    if (!tabInitialized && data?.current) {
      setTab("current");
      setTabInitialized(true);
    }
  }, [data?.current, tabInitialized]);

  const handleAccept = async (orderId: string) => {
    setAssignPending(orderId);
    try {
      await driverApi.acceptOrder(orderId);
      await refresh();
    } finally {
      setAssignPending(null);
    }
  };

  const handleReject = async (orderId: string) => {
    setAssignPending(orderId);
    try {
      await driverApi.rejectOrder(orderId);
      await refresh();
    } finally {
      setAssignPending(null);
    }
  };

  const cardProps = {
    onAccept: handleAccept,
    onReject: handleReject,
    actionPending: assignPending,
  };

  useEffect(() => {
    hasDriverSession().then((ok) => {
      if (!ok) router.replace("/login");
    });
  }, [router]);

  const tabs: { id: Tab; label: string; count: number }[] = [
    { id: "all", label: "All Jobs", count: data?.jobs.length ?? 0 },
    { id: "current", label: "Current", count: data?.current ? 1 : 0 },
    { id: "upcoming", label: "Upcoming", count: data?.upcoming.length ?? 0 },
    { id: "completed", label: "Completed", count: data?.completed.length ?? 0 },
    { id: "history", label: "Order History", count: history.length },
  ];

  const list = (() => {
    if (!data) return [];
    switch (tab) {
      case "current":
        return data.current ? [data.current] : [];
      case "upcoming":
        return data.upcoming;
      case "completed":
        return data.completed;
      case "history":
        return history;
      default:
        return data.jobs;
    }
  })();

  return (
    <DriverShell>
      <header className="flex flex-col gap-2 border-b border-[var(--primary)]/8 pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium text-[var(--muted)]">Driver Jobs</p>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Jobs List</h1>
          {lastUpdatedLabel && (
            <p className="mt-1 text-xs text-[var(--muted)]">
              Live · Updated {lastUpdatedLabel}
              <button type="button" onClick={refresh} className="ml-2 font-semibold text-[var(--secondary)]">
                Refresh
              </button>
            </p>
          )}
        </div>
        {data?.route_id && (
          <p className="text-sm text-[var(--muted)]">
            Route <span className="font-semibold text-[var(--primary)]">{data.route_id}</span>
            {data.route_status ? ` · ${data.route_status}` : ""}
            {data.route_metrics?.distance_km != null && (
              <>
                {" "}
                · {data.route_metrics.distance_km} km
                {data.route_metrics.duration_minutes != null
                  ? ` · ~${data.route_metrics.duration_minutes} min`
                  : ""}
              </>
            )}
          </p>
        )}
      </header>

      {data && data.optimize_available && tab !== "history" && tab !== "completed" && (
        <section className="mt-4 flex flex-col gap-3 rounded-2xl border border-[var(--secondary)]/20 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="flex items-center gap-2 text-sm font-semibold text-[var(--primary)]">
              <Route className="h-4 w-4 text-[var(--secondary)]" />
              Route order saves time & fuel
            </p>
            <p className="mt-1 text-xs text-[var(--muted)]">
              Priority numbers rank stops by shortest path across pickup and delivery addresses.
            </p>
            {optimizeMessage && (
              <p className="mt-2 text-xs font-semibold text-emerald-700">{optimizeMessage}</p>
            )}
          </div>
          <button
            type="button"
            onClick={() => void optimize()}
            disabled={optimizing}
            className="shrink-0 rounded-xl bg-[var(--secondary)] px-5 py-2.5 text-sm font-bold text-white disabled:opacity-60"
          >
            {optimizing ? "Optimizing…" : "Optimize route"}
          </button>
        </section>
      )}

      {loading && !data && (
        <div className="mt-8 animate-pulse space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-32 rounded-2xl bg-white" />
          ))}
        </div>
      )}

      {error && <p className="mt-4 text-red-600">{error}</p>}

      {data && (
        <>
          {data.current && (
            <section className="mt-6">
              <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-[var(--muted)]">
                <Briefcase className="h-4 w-4 text-[var(--secondary)]" />
                Current Job
              </h2>
              <JobCard job={data.current} highlight {...cardProps} />
            </section>
          )}

          <div className="mt-6 flex gap-2 overflow-x-auto pb-1">
            {tabs.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                className={cn(
                  "shrink-0 rounded-full px-4 py-2 text-sm font-semibold transition",
                  tab === t.id
                    ? "bg-[var(--primary)] text-white"
                    : "bg-white text-[var(--primary)]/70 hover:bg-[var(--gray-bg)]"
                )}
              >
                {t.label}
                <span className="ml-1.5 opacity-70">({t.count})</span>
              </button>
            ))}
          </div>

          <section className="mt-6">
            {tab === "upcoming" && (
              <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--muted)]">
                <Clock className="h-4 w-4" /> Upcoming Jobs
              </h2>
            )}
            {tab === "completed" && (
              <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--muted)]">
                <CheckCircle2 className="h-4 w-4" /> Completed Jobs
              </h2>
            )}
            {tab === "history" && (
              <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--muted)]">
                <History className="h-4 w-4" /> Order History
              </h2>
            )}

            {list.length === 0 ? (
              <p className="rounded-2xl bg-white p-8 text-center text-[var(--muted)]">
                No jobs in this view
              </p>
            ) : (
              <ul className="space-y-3">
                {list.map((job) => (
                  <li key={job.order_id}>
                    <JobCard
                      job={job}
                      highlight={Boolean(job.is_current_job || job.order_id === data.current?.order_id)}
                      {...cardProps}
                    />
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </DriverShell>
  );
}
