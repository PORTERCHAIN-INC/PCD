"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, Check, Loader2, Route, Send, Undo2, X, Zap } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useApiData } from "@/hooks/useApiData";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { ops } from "@/lib/operations";
import { dispatch, optimizeToast } from "@/lib/dispatch";
import { ordersApi } from "@/lib/orders";
import type { MapLine, MapPoint } from "@/components/maps/OsmMap";
import {
  ago,
  buildIssues,
  filterCounts,
  filterIssues,
  glide,
  kpis,
  promiseTimeline,
  type TodayFilter,
  type Pos,
  type TodayIssue,
} from "@/lib/today";

const OsmMap = dynamic(() => import("@/components/maps/OsmMap").then((m) => m.OsmMap), {
  ssr: false,
  loading: () => <div className="h-full w-full bg-[#0B1426]" />,
});

/** Theme: navy + one accent (electric blue for actions + live vehicles). Status colour = risk only. */
const ACCENT = "#3B82F6";
const RISK: Record<string, string> = {
  critical: "#EF4444",
  high: "#F59E0B",
  medium: "#94A3B8",
  low: "#475569",
};
const REFRESH_MS = 15_000;

const FILTERS: { key: TodayFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "late", label: "Late" },
  { key: "unassigned", label: "Unassigned" },
  { key: "failed", label: "Failed" },
];

const hhmm = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleTimeString("en-CA", { hour: "numeric", minute: "2-digit" }) : null;

function useTicker(ms: number) {
  const [n, setN] = useState(0);
  useEffect(() => {
    const id = setInterval(() => {
      if (document.visibilityState === "visible") setN((x) => x + 1);
    }, ms);
    return () => clearInterval(id);
  }, [ms]);
  return n;
}

function Kpi({ label, value, tone }: { label: string; value: string; tone?: "risk" | "ok" }) {
  return (
    <div className="min-w-0">
      <div className="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">
        {label}
      </div>
      <div
        className={cn(
          "mt-0.5 text-[28px] font-semibold leading-none tabular-nums",
          tone === "risk" ? "text-amber-400" : "text-white"
        )}
      >
        {value}
      </div>
    </div>
  );
}

function IssueRow({
  issue,
  active,
  onSelect,
  onChanged,
}: {
  issue: TodayIssue;
  active: boolean;
  onSelect: () => void;
  onChanged: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const fix = issue.item?.fixes?.[0];

  const act = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setBusy(true);
    setNote(null);
    try {
      const t = await getApiToken();
      if (issue.action === "fix" && fix && issue.item) {
        await dispatch.applyFix(t, issue.item, fix);
        setNote("Done");
      } else {
        const r = await dispatch.offer(t, issue.order_id);
        setNote(
          r.offer
            ? `Offered · ${Math.round(r.offer.seconds_left / 60)} min to accept`
            : "No eligible driver"
        );
      }
      onChanged();
    } catch (err) {
      setNote(err instanceof Error ? err.message : "Failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <li>
      <div
        role="button"
        tabIndex={0}
        onClick={onSelect}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onSelect()}
        aria-pressed={active}
        className={cn(
          "group flex w-full items-center gap-3 border-l-2 px-4 py-3 text-left outline-none transition-colors focus-visible:bg-white/5",
          active ? "border-[#3B82F6] bg-white/[0.06]" : "border-transparent hover:bg-white/[0.03]"
        )}
      >
        <span
          className="h-2 w-2 shrink-0 rounded-full"
          style={{ background: RISK[issue.severity] }}
          aria-label={issue.severity}
        />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-semibold text-white">{issue.label}</span>
          <span className="block truncate text-xs text-slate-400">
            <span className="tabular-nums text-slate-300">{issue.order_number}</span>
            {(() => {
              const sub = (
                note ||
                issue.detail ||
                issue.item?.state?.replaceAll("_", " ") ||
                ""
              ).trim();
              return sub ? ` · ${sub}` : null;
            })()}
          </span>
        </span>
        <span
          className={cn(
            "shrink-0 text-xs tabular-nums",
            (issue.age_min ?? 0) >= 15 ? "text-amber-400" : "text-slate-500"
          )}
        >
          {issue.age_min == null ? "" : `${issue.age_min}m`}
        </span>
        {issue.action !== "open" && (
          <button
            type="button"
            onClick={act}
            disabled={busy}
            title={issue.action === "fix" ? fix?.label : "Offer to best driver"}
            className="inline-flex h-8 shrink-0 items-center gap-1 rounded-lg bg-[#3B82F6] px-2.5 text-xs font-semibold text-white hover:bg-[#2563EB] disabled:opacity-50"
          >
            {busy ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : issue.action === "fix" ? (
              <Check className="h-3.5 w-3.5" />
            ) : (
              <Send className="h-3.5 w-3.5" />
            )}
            <span className="max-w-[6rem] truncate">
              {issue.action === "fix" ? (fix?.label ?? "Fix") : "Assign"}
            </span>
          </button>
        )}
      </div>
    </li>
  );
}

function Inspector({ orderId, onClose }: { orderId: string; onClose: () => void }) {
  const { data, loading } = useApiData((t) => ordersApi.detail(t, orderId), [orderId], {
    key: "today-order",
    staleTime: 10_000,
  });
  const eta = useApiData((t) => dispatch.liveEta(t), [], { key: "today-eta" }).data?.items.find(
    (e) => e.order_id === orderId
  );
  const steps = data ? promiseTimeline(data.state, data.timeline) : [];
  const driver = data?.driver as Record<string, unknown> | null | undefined;
  const driverName = (driver?.name ?? driver?.first_name ?? null) as string | null;
  const etaText = hhmm(eta?.eta);

  return (
    <aside
      aria-label="Selected order"
      className="absolute bottom-4 left-4 right-4 z-10 rounded-xl border border-[#1E2A44] bg-[#111C33]/95 p-4 text-white backdrop-blur md:left-auto md:w-[380px]"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs uppercase tracking-[0.12em] text-slate-400">
            {data?.order_number ?? "Order"} · {data?.state?.replaceAll("_", " ") ?? "…"}
          </div>
          <div className="mt-1 text-[28px] font-semibold leading-tight tabular-nums">
            {etaText ? `ETA ${etaText}` : data?.state === "delivered" ? "Delivered" : "No live ETA"}
          </div>
          <div className="text-sm text-slate-400">
            {eta?.promise ? `Promised ${hhmm(eta.promise)} · ` : ""}
            {driverName ?? "No driver yet"}
            {eta && !eta.has_gps ? " · no GPS" : ""}
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="rounded-lg p-1.5 text-slate-400 hover:bg-white/10 hover:text-white"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      {loading && !data ? (
        <p className="mt-4 text-xs text-slate-400">Loading…</p>
      ) : (
        <ol className="mt-4 grid grid-cols-4 gap-2" aria-label="Status timeline">
          {steps.map((s) => (
            <li key={s.label} className="min-w-0">
              <div className={cn("h-1 rounded-full", s.done ? "bg-[#3B82F6]" : "bg-[#1E2A44]")} />
              <div
                className={cn("mt-1.5 truncate text-xs", s.done ? "text-white" : "text-slate-500")}
              >
                {s.label}
              </div>
              <div className="text-[11px] tabular-nums text-slate-500">{hhmm(s.at) ?? ""}</div>
            </li>
          ))}
        </ol>
      )}
      <div className="mt-3 truncate text-xs text-slate-400">
        {data ? `${data.pickup} → ${data.destination}` : ""}
      </div>
      <Link
        href={`/orders/${orderId}`}
        className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-[#60A5FA] hover:underline"
      >
        Full order <ArrowUpRight className="h-4 w-4" />
      </Link>
    </aside>
  );
}

const GLIDE_MS = 1800;

/** Smoothly move markers from the last poll to the new one (prep for WebSocket pushes). */
function useGlide<T extends Pos>(target: T[]): T[] {
  const [shown, setShown] = useState<T[]>(target);
  const last = useRef<Pos[]>(target);
  useEffect(() => {
    const from = last.current;
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduce || from.length === 0) {
      last.current = target;
      setShown(target);
      return;
    }
    const start = performance.now();
    let raf = 0;
    let lastPaint = 0;
    const step = (now: number) => {
      const t = (now - start) / GLIDE_MS;
      if (now - lastPaint > 33 || t >= 1) {
        lastPaint = now;
        const frame = glide(from, target, t);
        last.current = frame;
        setShown(frame);
      }
      if (t < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target]);
  return shown;
}

type Toast = { text: string; planId?: string; tone?: "ok" | "error" };

/** Fill the viewport below wherever the shell places us (banners vary). */
function useFillHeight() {
  const ref = useRef<HTMLDivElement>(null);
  const [h, setH] = useState<number | null>(null);
  useEffect(() => {
    const calc = () => {
      if (ref.current)
        setH(Math.max(560, window.innerHeight - ref.current.getBoundingClientRect().top));
    };
    calc();
    window.addEventListener("resize", calc);
    const ro = new ResizeObserver(calc);
    ro.observe(document.body);
    return () => {
      window.removeEventListener("resize", calc);
      ro.disconnect();
    };
  }, []);
  return { ref, h };
}

/** Cached query data exists only in the browser; render data after mount so SSR == first paint. */
export function TodayOps() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) {
    return (
      <div
        aria-busy
        className="today-ops h-[calc(100dvh-7rem)] rounded-xl border border-[#1E2A44] bg-[#0B1426]"
      />
    );
  }
  return <TodayOpsLive />;
}

function TodayOpsLive() {
  const fill = useFillHeight();
  const tick = useTicker(REFRESH_MS);
  const qc = useQueryClient();
  const { getApiToken } = useAdminAuth();
  const [filter, setFilter] = useState<TodayFilter>("all");
  const [selected, setSelected] = useState<string | null>(null);
  const [toast, setToast] = useState<Toast | null>(null);
  const [undoing, setUndoing] = useState(false);
  useEffect(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast(null), toast.planId ? 20_000 : 6_000);
    return () => clearTimeout(id);
  }, [toast]);
  const [planning, setPlanning] = useState(false);

  // Instant data: cached snapshot renders first (keepPreviousData), refresh is quiet.
  const opts = { staleTime: 5_000 };
  const stats = useApiData((t) => ops.stats(t), [], { key: "today-stats", ...opts });
  const exc = useApiData((t) => dispatch.exceptions(t), [], { key: "today-exceptions", ...opts });
  const queue = useApiData((t) => ops.queue(t), [], { key: "today-queue", ...opts });
  const etas = useApiData((t) => dispatch.liveEta(t), [], { key: "today-eta", ...opts });
  const live = useApiData((t) => ops.liveMap(t), [], { key: "today-map", ...opts });
  const route = useApiData((t) => ops.routeGeometry(t, selected ?? ""), [selected], {
    key: "today-route",
    enabled: !!selected,
    staleTime: 60_000,
  });

  const refetchAll = () => qc.invalidateQueries({ queryKey: ["admin"], refetchType: "active" });
  useEffect(() => {
    if (tick > 0) void refetchAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tick]);

  const [syncedAt, setSyncedAt] = useState<number | null>(null);
  const fetching = stats.isFetching || exc.isFetching || live.isFetching;
  useEffect(() => {
    if (!fetching && (stats.data || live.data)) setSyncedAt(Date.now());
  }, [fetching, stats.data, live.data]);

  const issues = useMemo(
    () => buildIssues(exc.data?.items ?? [], queue.data ?? []),
    [exc.data, queue.data]
  );
  const counts = filterCounts(issues);
  const shown = filterIssues(issues, filter);
  const k = kpis(stats.data, etas.data?.items ?? [], issues);
  const riskByOrder = useMemo(() => {
    const m = new Map<string, string>();
    for (const i of issues) if (!m.has(i.order_id)) m.set(i.order_id, i.severity);
    return m;
  }, [issues]);

  const driverTargets = useMemo(() => live.data?.drivers ?? [], [live.data]);
  const glidingDrivers = useGlide(driverTargets);

  const points = useMemo<MapPoint[]>(() => {
    const snap = live.data;
    if (!snap) return [];
    const stops: MapPoint[] = snap.orders.flatMap((o) =>
      o.stops.map((s, idx) => {
        const risk = riskByOrder.get(o.id);
        return {
          id: o.id,
          lat: s.lat,
          lng: s.lng,
          size: o.id === selected ? 7 : 4,
          color: risk ? RISK[risk] : s.kind === "pickup" ? "#CBD5E1" : "#64748B",
          ring: o.id === selected ? ACCENT : "#0B1426",
          title: `${o.tracking_number} · ${s.label} ${idx + 1}`,
        };
      })
    );
    const drivers: MapPoint[] = glidingDrivers.map((d) => ({
      id: `driver:${d.id}`,
      lat: d.lat,
      lng: d.lng,
      size: 8,
      color: d.online ? ACCENT : "#334155",
      ring: d.online ? "#BFDBFE" : "#0B1426",
      title: d.name,
    }));
    return [...stops, ...drivers];
  }, [live.data, glidingDrivers, riskByOrder, selected]);

  const lines = useMemo<MapLine[]>(() => {
    const p = route.data?.path;
    return selected && p?.length
      ? [{ id: "sel", path: p, color: ACCENT, width: 4, opacity: 0.9 }]
      : [];
  }, [route.data, selected]);

  const onlineDrivers = live.data?.drivers.filter((d) => d.online).length ?? 0;
  const gpsDrivers = live.data?.drivers.length ?? 0;
  const firstLoad = !stats.data && !exc.data && (stats.loading || exc.loading);
  const loadError = stats.error || exc.error || live.error;

  // Ravi (Oct 14): optimizing applies the plan immediately; Undo is the safety net.
  const optimize = async () => {
    setPlanning(true);
    setToast(null);
    try {
      const plan = await dispatch.planDay(await getApiToken(), { time_limit_s: 10, commit: true });
      const assigned = plan.summary.commit?.assigned ?? 0;
      setToast({ text: optimizeToast(plan), planId: assigned > 0 ? plan.id : undefined });
      void refetchAll();
    } catch (e) {
      setToast({ text: e instanceof Error ? e.message : "Optimize failed", tone: "error" });
    } finally {
      setPlanning(false);
    }
  };

  const undo = async (planId: string) => {
    setUndoing(true);
    try {
      const r = await dispatch.undoPlan(await getApiToken(), planId);
      setToast({
        text: `Undone · ${r.released} released${r.kept.length ? ` · ${r.kept.length} kept (already moving)` : ""}`,
      });
      void refetchAll();
    } catch (e) {
      setToast({ text: e instanceof Error ? e.message : "Undo failed", tone: "error" });
    } finally {
      setUndoing(false);
    }
  };

  return (
    <div
      ref={fill.ref}
      style={fill.h ? { height: fill.h } : undefined}
      className="today-ops relative flex h-[calc(100dvh-7rem)] flex-col overflow-hidden rounded-xl border border-[#1E2A44] bg-[#0B1426] text-white"
    >
      {/* Top strip: 4 numbers only + two actions */}
      <header className="flex flex-wrap items-center gap-x-10 gap-y-3 border-b border-[#1E2A44] px-5 py-4">
        <div className="mr-2">
          <h1 className="text-xl font-semibold tracking-tight">Today</h1>
          <div className="flex items-center gap-1.5 text-xs text-slate-400" aria-live="polite">
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                loadError ? "bg-red-500" : "bg-emerald-400"
              )}
            />
            {loadError ? "Offline · showing last data" : `Synced ${ago(syncedAt)}`}
          </div>
        </div>
        <Kpi label="On time" value={k.onTimePct == null ? "—" : `${k.onTimePct}%`} />
        <Kpi
          label="Unassigned"
          value={String(k.unassigned)}
          tone={k.unassigned ? "risk" : undefined}
        />
        <Kpi label="At risk" value={String(k.atRisk)} tone={k.atRisk ? "risk" : undefined} />
        <Kpi label="Done" value={`${k.done}/${k.total}`} />
        <div className="ml-auto flex items-center gap-2">
          <button
            type="button"
            onClick={optimize}
            disabled={planning}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-[#3B82F6] px-3.5 text-sm font-semibold text-white hover:bg-[#2563EB] disabled:opacity-50"
          >
            {planning ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Route className="h-4 w-4" />
            )}
            Optimize routes
          </button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        {/* Left 30%: exception queue, worst first */}
        <section
          aria-label="Exceptions"
          className="flex max-h-[45vh] min-h-0 flex-col border-[#1E2A44] md:max-h-none md:w-[30%] md:min-w-[320px] md:border-r"
        >
          <div className="flex gap-1 px-3 pt-3 pb-2" role="tablist">
            {FILTERS.map((f) => (
              <button
                key={f.key}
                role="tab"
                aria-selected={filter === f.key}
                onClick={() => setFilter(f.key)}
                className={cn(
                  "rounded-lg px-2.5 py-1.5 text-xs font-medium tabular-nums",
                  filter === f.key ? "bg-white/10 text-white" : "text-slate-400 hover:text-white"
                )}
              >
                {f.label} <span className="text-slate-500">{counts[f.key]}</span>
              </button>
            ))}
          </div>
          <ul className="min-h-0 flex-1 divide-y divide-[#1E2A44]/60 overflow-y-auto">
            {firstLoad &&
              Array.from({ length: 6 }).map((_, i) => (
                <li key={i} className="mx-4 my-3 h-10 animate-pulse rounded-lg bg-white/5" />
              ))}
            {shown.map((i) => (
              <IssueRow
                key={i.key}
                issue={i}
                active={selected === i.order_id}
                onSelect={() => setSelected(i.order_id === selected ? null : i.order_id)}
                onChanged={refetchAll}
              />
            ))}
            {!firstLoad && shown.length === 0 && (
              <li className="flex flex-col items-center gap-2 px-6 py-16 text-center">
                <Zap className="h-6 w-6 text-[#3B82F6]" />
                <span className="text-sm font-semibold">Nothing needs you.</span>
                <span className="text-xs text-slate-400">
                  {filter === "all" ? "Every order is on track." : "No orders in this filter."}
                </span>
              </li>
            )}
          </ul>
          <nav className="flex flex-wrap gap-x-4 gap-y-1 border-t border-[#1E2A44] px-4 py-2.5 text-xs text-slate-400">
            <Link href="/orders" className="hover:text-white">
              Orders
            </Link>
            <Link href="/dispatch/plan" className="hover:text-white">
              Plan
            </Link>
            <Link href="/dispatch/fleet" className="hover:text-white">
              Fleet
            </Link>
            <Link href="/dispatch/today" className="hover:text-white">
              Classic dispatch
            </Link>
          </nav>
        </section>

        {/* Right 70%: live map */}
        <section aria-label="Live map" className="relative min-h-[320px] flex-1">
          {/* maplibre forces position:relative on its container, so size via a wrapper. */}
          <div className="absolute inset-0">
            <OsmMap
              tone="navy"
              label="Live drivers and stops"
              points={points}
              lines={lines}
              fit={!selected}
              onPointClick={(id) => {
                if (!id.startsWith("driver:")) setSelected(id);
              }}
              className="h-full w-full"
            />
          </div>
          <div className="pointer-events-none absolute left-4 top-4 z-10 flex gap-3 rounded-lg border border-[#1E2A44] bg-[#0B1426]/85 px-3 py-2 text-xs text-slate-300 backdrop-blur">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-[#3B82F6]" /> {onlineDrivers} live
            </span>
            <span className="text-slate-500">{gpsDrivers} with GPS consent</span>
            <span className="text-slate-500">{live.data?.orders.length ?? 0} in flight</span>
          </div>
          {selected && <Inspector orderId={selected} onClose={() => setSelected(null)} />}
        </section>
      </div>
      {toast && (
        <div
          role="status"
          aria-live="polite"
          className={cn(
            "absolute bottom-6 left-1/2 z-20 flex -translate-x-1/2 items-center gap-4 rounded-xl border px-4 py-3 text-sm shadow-none",
            toast.tone === "error"
              ? "border-red-500/40 bg-[#2A1220] text-red-200"
              : "border-[#1E2A44] bg-[#111C33] text-white"
          )}
        >
          <span className="tabular-nums">{toast.text}</span>
          {toast.planId && (
            <button
              type="button"
              onClick={() => undo(toast.planId!)}
              disabled={undoing}
              className="inline-flex items-center gap-1.5 font-semibold text-[#60A5FA] hover:text-white disabled:opacity-50"
            >
              {undoing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Undo2 className="h-4 w-4" />
              )}
              Undo
            </button>
          )}
          <Link href="/dispatch/plan" className="text-xs text-slate-400 hover:text-white">
            View plan
          </Link>
          <button
            type="button"
            onClick={() => setToast(null)}
            aria-label="Dismiss"
            className="text-slate-500 hover:text-white"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
}
