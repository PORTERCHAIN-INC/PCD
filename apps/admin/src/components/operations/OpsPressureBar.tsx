"use client";

import { useState } from "react";
import { AlertTriangle, Boxes, ClipboardList, Package, Timer, Wallet, Zap } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import type { OpsStats } from "@/lib/operations";
import { money } from "@/lib/crmFormat";
import type { OpsViewId } from "@/components/operations/opsViews";

type Tone = "ok" | "warn" | "danger" | "neutral";

const TONE_STYLES: Record<Tone, { ring: string; value: string; icon: string }> = {
  ok: { ring: "border-green-200 bg-green-50/40", value: "text-green-700", icon: "text-green-600" },
  warn: {
    ring: "border-amber-200 bg-amber-50/50",
    value: "text-amber-700",
    icon: "text-amber-600",
  },
  danger: { ring: "border-red-200 bg-red-50/50", value: "text-red-700", icon: "text-red-600" },
  neutral: {
    ring: "border-primary/10 bg-white",
    value: "text-primary",
    icon: "text-secondary",
  },
};

type PressureTile = {
  id: string;
  label: string;
  value: string;
  tone: Tone;
  icon: React.ComponentType<{ className?: string }>;
  drill: OpsViewId;
};

/** Action-pressure KPIs only — vanity “today” metrics live in the Today popover. */
export function OpsPressureBar({
  stats,
  onDrill,
}: {
  stats: OpsStats;
  onDrill?: (target: OpsViewId) => void;
}) {
  const [todayOpen, setTodayOpen] = useState(false);
  const slaRisk = stats.sla_at_risk ?? 0;
  const slaBreached = stats.sla_breached ?? 0;
  const slaTotal = slaRisk + slaBreached;
  const deltas = stats.deltas ?? {};

  const tiles: PressureTile[] = [
    {
      id: "waiting",
      label: "Waiting",
      value: String(stats.waiting_dispatch),
      tone: stats.waiting_dispatch >= 15 ? "danger" : stats.waiting_dispatch >= 5 ? "warn" : "ok",
      icon: ClipboardList,
      drill: "desk",
    },
    {
      id: "delayed",
      label: "Delayed",
      value: String(stats.delayed_orders),
      tone: stats.delayed_orders >= 5 ? "danger" : stats.delayed_orders > 0 ? "warn" : "ok",
      icon: Zap,
      drill: "orders",
    },
    {
      id: "sla",
      label: "SLA",
      value: String(slaTotal),
      tone: slaBreached > 0 ? "danger" : slaRisk > 0 ? "warn" : "ok",
      icon: Timer,
      drill: "attention",
    },
    {
      id: "exceptions",
      label: "Exceptions",
      value: String(stats.open_exceptions),
      tone: stats.open_exceptions >= 5 ? "danger" : stats.open_exceptions > 0 ? "warn" : "ok",
      icon: AlertTriangle,
      drill: "attention",
    },
  ];

  return (
    <div className="flex flex-wrap items-stretch gap-2">
      <div className="ops-stat-grid grid min-w-0 flex-1 grid-cols-2 gap-2 sm:grid-cols-4">
        {tiles.map((k) => {
          const styles = TONE_STYLES[k.tone];
          const Icon = k.icon;
          const Comp = onDrill ? "button" : "div";
          return (
            <Comp
              key={k.id}
              type={onDrill ? "button" : undefined}
              onClick={onDrill ? () => onDrill(k.drill) : undefined}
              title={onDrill ? `Open ${k.label}` : undefined}
              className={cn(
                "rounded-xl border p-3 text-left transition-shadow",
                styles.ring,
                onDrill &&
                  "cursor-pointer hover:shadow-md focus:outline-none focus:ring-2 focus:ring-secondary/40"
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <p className="text-[11px] font-medium text-muted">{k.label}</p>
                <Icon className={cn("h-3.5 w-3.5", styles.icon)} />
              </div>
              <p className={cn("mt-1 text-lg font-bold tabular-nums", styles.value)}>{k.value}</p>
            </Comp>
          );
        })}
      </div>

      <div className="relative">
        <button
          type="button"
          onClick={() => setTodayOpen((v) => !v)}
          className="flex h-full min-w-[7.5rem] flex-col justify-center rounded-xl border border-primary/10 bg-white px-3 py-2 text-left hover:bg-gray-bg/40"
          title="Today snapshot"
        >
          <p className="text-[11px] font-medium text-muted">Today</p>
          <p className="text-sm font-semibold tabular-nums text-primary">
            {stats.active_deliveries} active
          </p>
        </button>
        {todayOpen && (
          <>
            <div className="fixed inset-0 z-20" onClick={() => setTodayOpen(false)} aria-hidden />
            <div className="absolute right-0 z-30 mt-1 w-56 rounded-xl border border-primary/10 bg-white p-3 shadow-lg">
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted">
                Today
              </p>
              <ul className="space-y-2 text-sm text-primary">
                <li className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-muted">
                    <Package className="h-3.5 w-3.5" /> Orders
                  </span>
                  <span className="font-semibold tabular-nums">
                    {stats.orders_today}
                    {deltas.orders_today != null && deltas.orders_today !== 0 && (
                      <span className="ml-1 text-[11px] font-medium text-muted">
                        {deltas.orders_today > 0 ? "+" : ""}
                        {deltas.orders_today}
                      </span>
                    )}
                  </span>
                </li>
                <li className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-muted">
                    <Boxes className="h-3.5 w-3.5" /> Completed
                  </span>
                  <span className="font-semibold tabular-nums">
                    {stats.completed_today}
                    {deltas.completed_today != null && deltas.completed_today !== 0 && (
                      <span className="ml-1 text-[11px] font-medium text-muted">
                        {deltas.completed_today > 0 ? "+" : ""}
                        {deltas.completed_today}
                      </span>
                    )}
                  </span>
                </li>
                <li className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-muted">
                    <Wallet className="h-3.5 w-3.5" /> Revenue
                  </span>
                  <span className="font-semibold tabular-nums">
                    {money(stats.revenue_today_cents)}
                  </span>
                </li>
              </ul>
              {onDrill && (
                <button
                  type="button"
                  className="mt-3 w-full rounded-lg border border-primary/10 px-2 py-1.5 text-xs font-medium text-secondary hover:bg-gray-bg"
                  onClick={() => {
                    setTodayOpen(false);
                    onDrill("orders");
                  }}
                >
                  Open Active Orders
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
