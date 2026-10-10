"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, Inbox, MoreHorizontal } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { LOST_REASONS, leadsApi, type SpeedWindow } from "@/lib/leads";

/* Musk-style lead desk primitives: one navy strip, one accent, lots of air. */

const fmtPct = (v: number | null) => (v == null ? "—" : `${Math.round(v)}%`);
const fmtMin = (v: number | null) =>
  v == null
    ? "—"
    : v < 60
      ? `${v < 10 ? v.toFixed(1) : Math.round(v)}m`
      : `${(v / 60).toFixed(1)}h`;

function Metric({ label, value, goal }: { label: string; value: string; goal?: boolean }) {
  return (
    <div className="min-w-0">
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-300">
        {label}
      </p>
      <p
        className={cn(
          "mt-1 text-2xl font-extrabold tabular-nums tracking-tight sm:text-3xl",
          goal ? "text-sky-300" : "text-white"
        )}
      >
        {value}
      </p>
    </div>
  );
}

/** Speed metrics strip — the first thing on the Inbox. Goal: reply in < 5 min. */
export function LeadSpeedStrip() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const [days, setDays] = useState<7 | 30>(7);
  const { data, isLoading } = useQuery({
    queryKey: ["lead-speed"],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => leadsApi.speed(await getApiToken()),
    refetchInterval: 60_000,
  });
  const { data: weekly } = useQuery({
    queryKey: ["lead-weekly"],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => leadsApi.weeklySummary(await getApiToken()),
  });
  const w: SpeedWindow | undefined = data?.windows.find((x) => x.days === days);
  const top = (w?.win_rate_by_channel ?? []).filter((c) => c.won + c.lost > 0).slice(0, 3);
  return (
    <section
      aria-label="Lead speed"
      className="rounded-3xl bg-primary px-5 py-5 text-white shadow-sm sm:px-7 sm:py-6"
    >
      <div className="mb-4 flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-white">
          Speed{" "}
          <span className="font-normal text-slate-300">· goal: every lead answered in 5 min</span>
        </p>
        <div
          role="group"
          aria-label="Window"
          className="flex rounded-full bg-white/10 p-0.5 text-xs font-semibold"
        >
          {([7, 30] as const).map((d) => (
            <button
              key={d}
              type="button"
              aria-pressed={days === d}
              onClick={() => setDays(d)}
              className={cn(
                "rounded-full px-3 py-1",
                days === d ? "bg-white text-primary" : "text-slate-200 hover:text-white"
              )}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>
      {isLoading || !w ? (
        <div className="grid grid-cols-2 gap-5 sm:grid-cols-5" aria-busy="true">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-xl bg-white/10" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-x-5 gap-y-5 sm:grid-cols-5">
          <Metric label="Median 1st reply" value={fmtMin(w.median_first_reply_minutes)} goal />
          <Metric label="Answered < 5 min" value={fmtPct(w.answered_within_5m_pct)} goal />
          <Metric label="Quote → booking" value={fmtPct(w.quote_to_booking_pct)} />
          <Metric label="Booking → repeat" value={fmtPct(w.booking_to_repeat_pct)} />
          <div className="col-span-2 hidden min-w-0 sm:col-span-1 sm:block">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-300">
              Win rate by channel
            </p>
            {top.length ? (
              <ul className="mt-1.5 space-y-0.5 text-sm">
                {top.map((c) => (
                  <li key={c.channel} className="flex justify-between gap-3 tabular-nums">
                    <span className="truncate capitalize text-slate-200">
                      {c.channel.replace(/_/g, " ")}
                    </span>
                    <span className="font-bold text-white">{fmtPct(c.win_rate)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-1.5 text-sm text-slate-300">No closed leads yet</p>
            )}
          </div>
        </div>
      )}
      {weekly && weekly.won + weekly.lost > 0 ? (
        <p className="mt-5 hidden border-t border-white/10 pt-3 text-xs text-slate-300 sm:block">
          This week: <span className="font-semibold text-white">{weekly.won} won</span> ·{" "}
          <span className="font-semibold text-white">{weekly.lost} lost</span>
          {weekly.lost_reasons[0] ? (
            <>
              {" "}
              · top loss reason{" "}
              <span className="font-semibold text-white">
                {LOST_REASONS.find((r) => r.key === weekly.lost_reasons[0].reason)?.label ??
                  weekly.lost_reasons[0].reason}
              </span>
            </>
          ) : null}
          {weekly.by_channel.length ? (
            <>
              {" "}
              ·{" "}
              {weekly.by_channel
                .map((c) => `${c.channel.replace(/_/g, " ")} ${c.won}/${c.won + c.lost}`)
                .join(", ")}
            </>
          ) : null}
        </p>
      ) : null}
    </section>
  );
}

/** Compact secondary-actions menu (closes on outside click / Escape). */
export function MoreMenu({ label = "More", children }: { label?: string; children: ReactNode }) {
  const ref = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const close = (e: MouseEvent | KeyboardEvent) => {
      const el = ref.current;
      if (!el?.open) return;
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !el.contains(e.target as Node)) {
        el.open = false;
      }
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, []);
  return (
    <details ref={ref} className="relative">
      <summary
        className="inline-flex cursor-pointer list-none items-center gap-1.5 rounded-full border border-primary/15 bg-white px-4 py-2 text-sm font-semibold text-primary hover:bg-slate-50 [&::-webkit-details-marker]:hidden"
        aria-label={label}
      >
        <MoreHorizontal className="h-4 w-4" aria-hidden /> {label}
      </summary>
      <div className="absolute right-0 z-30 mt-2 w-[min(92vw,26rem)] space-y-3 rounded-2xl border border-primary/10 bg-white p-4 shadow-xl">
        {children}
      </div>
    </details>
  );
}

/** Collapsible block for advanced filters. */
export function Disclosure({
  label,
  count,
  children,
}: {
  label: string;
  count?: number;
  children: ReactNode;
}) {
  return (
    <details className="group">
      <summary className="inline-flex cursor-pointer list-none items-center gap-1.5 rounded-full border border-primary/15 px-3.5 py-1.5 text-sm font-semibold text-primary hover:bg-slate-50 [&::-webkit-details-marker]:hidden">
        {label}
        {count ? (
          <span className="rounded-full bg-secondary px-1.5 text-[11px] font-bold text-white">
            {count}
          </span>
        ) : null}
        <ChevronDown className="h-4 w-4 transition group-open:rotate-180" aria-hidden />
      </summary>
      <div className="mt-3 space-y-3">{children}</div>
    </details>
  );
}

/** Designed empty state — never a blank box. */
export function EmptyState({
  title,
  hint,
  action,
}: {
  title: string;
  hint: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-16 text-center" role="status">
      <span className="mb-4 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-secondary/10 text-secondary">
        <Inbox className="h-7 w-7" aria-hidden />
      </span>
      <p className="text-lg font-bold text-primary">{title}</p>
      <p className="mt-1 max-w-sm text-sm text-slate-600">{hint}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}

/** Skeleton rows shaped like the inbox (no layout jump on load). */
export function InboxSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="divide-y divide-primary/5" aria-busy="true" role="status">
      <span className="sr-only">Loading leads</span>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 py-4">
          <div className="h-10 w-10 animate-pulse rounded-full bg-slate-100" />
          <div className="flex-1 space-y-2">
            <div className="h-3.5 w-1/3 animate-pulse rounded bg-slate-100" />
            <div className="h-3 w-1/2 animate-pulse rounded bg-slate-100" />
          </div>
          <div className="h-6 w-14 animate-pulse rounded-full bg-slate-100" />
        </div>
      ))}
    </div>
  );
}

/** Keyboard triage: j/k move, Enter open, x select, / search. Ignored while typing. */
export function useTriageKeys(opts: {
  count: number;
  onOpen: (i: number) => void;
  onToggle: (i: number) => void;
  searchRef: React.RefObject<HTMLInputElement | null>;
}) {
  const [cursor, setCursor] = useState(-1);
  const { count, onOpen, onToggle, searchRef } = opts;
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (t && (t.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName))) {
        if (e.key === "Escape") t.blur();
        return;
      }
      if (e.key === "/") {
        e.preventDefault();
        searchRef.current?.focus();
      } else if (e.key === "j" || e.key === "ArrowDown") {
        e.preventDefault();
        setCursor((c) => Math.min(count - 1, c + 1));
      } else if (e.key === "k" || e.key === "ArrowUp") {
        e.preventDefault();
        setCursor((c) => Math.max(0, c - 1));
      } else if (e.key === "Enter" && cursor >= 0) {
        onOpen(cursor);
      } else if (e.key === "x" && cursor >= 0) {
        onToggle(cursor);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [count, cursor, onOpen, onToggle, searchRef]);
  return cursor;
}

export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="rounded border border-primary/15 bg-slate-50 px-1.5 py-0.5 font-mono text-[11px] font-semibold text-primary">
      {children}
    </kbd>
  );
}
