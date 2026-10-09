"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Briefcase, History, Route } from "lucide-react";
import { CardListSkeleton } from "@porterchain/ui/loading";
import { EmptyState } from "@porterchain/ui/empty-state";
import DriverShell from "@/components/DriverShell";
import { JobCard } from "@/components/jobs/JobCard";
import { useDriverJobs } from "@/hooks/useDriverJobs";
import { driverApi, hasDriverSession } from "@/lib/api";
import { groupJobsByDay } from "@/lib/jobs";
import { cn } from "@/lib/utils";

type Tab = "today" | "earlier";

export default function JobsListClient() {
  const router = useRouter();
  const {
    data,
    history,
    error,
    historyError,
    loading,
    optimizing,
    optimizeMessage,
    preview,
    canUndo,
    lastUpdatedLabel,
    refresh,
    optimize,
    acceptPreview,
    discardPreview,
    undoOptimize,
  } = useDriverJobs();
  const [tab, setTab] = useState<Tab>("today");
  const deferredTab = useDeferredValue(tab);
  const [assignPending, setAssignPending] = useState<string | null>(null);

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

  const todayJobs = data?.jobs ?? [];
  const todayIds = useMemo(
    () => new Set((data?.jobs ?? []).map((job) => job.order_id)),
    [data?.jobs]
  );
  const earlier = useMemo(
    () => history.filter((job) => !todayIds.has(job.order_id)),
    [history, todayIds]
  );
  const earlierGroups = useMemo(() => groupJobsByDay(earlier), [earlier]);
  const restToday = todayJobs.filter((job) => job.order_id !== data?.current?.order_id);

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
    { id: "today", label: "Today", count: todayJobs.length },
    { id: "earlier", label: "Earlier", count: earlier.length },
  ];

  return (
    <DriverShell>
      <header className="flex flex-col gap-2 border-b border-[var(--primary)]/8 pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium text-[var(--muted)]">Driver Jobs</p>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Jobs List</h1>
          {lastUpdatedLabel && (
            <p className="mt-1 text-xs text-[var(--muted)]">
              Live · Updated {lastUpdatedLabel}
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

      {data && data.optimize_available && tab === "today" && (
        <section className="mt-4 flex flex-col gap-3 rounded-2xl border border-[var(--secondary)]/20 bg-white p-4 shadow-sm">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="flex items-center gap-2 text-sm font-semibold text-[var(--primary)]">
                <Route className="h-4 w-4 text-[var(--secondary)]" />
                Request stop order
              </p>
              <p className="mt-1 text-xs text-[var(--muted)]">
                Asks PorterChain for a stop order. Accept to apply it. Keep current leaves your
                route unchanged.
              </p>
              {optimizeMessage && (
                <p
                  className={`mt-2 text-xs font-semibold ${
                    preview ? "text-amber-800" : "text-emerald-700"
                  }`}
                >
                  {optimizeMessage}
                </p>
              )}
            </div>
            <div className="flex shrink-0 flex-wrap gap-2">
              {!preview && (
                <button
                  type="button"
                  onClick={() => void optimize()}
                  disabled={optimizing}
                  className="rounded-xl bg-[var(--secondary)] px-5 py-2.5 text-sm font-bold text-white disabled:opacity-60"
                >
                  {optimizing ? "Building preview…" : "Request stop order"}
                </button>
              )}
              {canUndo && !preview && (
                <button
                  type="button"
                  onClick={() => void undoOptimize()}
                  disabled={optimizing}
                  className="rounded-xl border border-[var(--primary)]/20 px-4 py-2.5 text-sm font-semibold text-[var(--primary)] disabled:opacity-60"
                >
                  Undo last apply
                </button>
              )}
            </div>
          </div>
          {preview && (
            <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-3">
              <p className="text-xs font-semibold text-amber-900">Preview — not applied yet</p>
              {(preview.optimized_stops?.length ?? 0) > 0 && (
                <ol className="mt-2 max-h-40 list-decimal space-y-1 overflow-y-auto pl-5 text-xs text-[var(--primary)]">
                  {preview.optimized_stops.slice(0, 24).map((stop, i) => (
                    <li key={`${String(stop.order_id)}-${i}`}>
                      {String(stop.stop_type || stop.type || "stop")} ·{" "}
                      {String(stop.order_id || stop.tracking_number || "—")}
                    </li>
                  ))}
                </ol>
              )}
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => void acceptPreview()}
                  disabled={optimizing}
                  className="rounded-xl bg-[var(--secondary)] px-4 py-2 text-sm font-bold text-white disabled:opacity-60"
                >
                  Accept new order
                </button>
                <button
                  type="button"
                  onClick={discardPreview}
                  disabled={optimizing}
                  className="rounded-xl border border-[var(--primary)]/20 px-4 py-2 text-sm font-semibold text-[var(--primary)] disabled:opacity-60"
                >
                  Keep current
                </button>
              </div>
            </div>
          )}
        </section>
      )}

      {loading && !data && <CardListSkeleton count={4} />}

      {error && <p className="mt-4 text-red-600">{error}</p>}

      {data && (
        <>
          {tab === "today" && data.current && (
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
                <span className="ml-1.5 opacity-90">({t.count})</span>
              </button>
            ))}
          </div>

          <section className="mt-6">
            {deferredTab === "earlier" ? (
              <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--muted)]">
                <History className="h-4 w-4" /> Earlier routes
              </h2>
            ) : null}

            {deferredTab === "earlier" && historyError ? (
              <p className="mb-3 text-sm text-red-600">{historyError}</p>
            ) : null}

            {deferredTab === "today" && restToday.length === 0 && !data.current ? (
              <EmptyState
                title="No jobs on this shift yet"
                hint="Refresh when new routes are dispatched."
                className="mt-2"
              />
            ) : null}

            {deferredTab === "today" && restToday.length > 0 ? (
              <ul className="space-y-3">
                {restToday.map((job) => (
                  <li key={job.order_id}>
                    <JobCard job={job} {...cardProps} />
                  </li>
                ))}
              </ul>
            ) : null}

            {deferredTab === "earlier" && earlier.length === 0 && !historyError ? (
              <EmptyState
                title="No earlier jobs"
                hint="Completed work from prior days shows up here."
                className="mt-2"
              />
            ) : null}

            {deferredTab === "earlier" && earlierGroups.length > 0 ? (
              <div className="space-y-6">
                {earlierGroups.map((group) => (
                  <div key={group.key}>
                    <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-[var(--muted)]">
                      {group.label} · {group.jobs.length} {group.jobs.length === 1 ? "job" : "jobs"}
                    </h3>
                    <ul className="space-y-3">
                      {group.jobs.map((job) => (
                        <li key={job.order_id}>
                          <JobCard job={job} />
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            ) : null}
          </section>
        </>
      )}
    </DriverShell>
  );
}
