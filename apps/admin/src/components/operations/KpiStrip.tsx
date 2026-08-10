"use client";

import {
  AlertTriangle,
  ClipboardList,
  Package,
  Timer,
  Truck,
  Wallet,
  Zap,
  Boxes,
} from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import type { OpsStats } from "@/lib/operations";
import { money } from "@/lib/crmFormat";

export type OpsDrillTarget =
  "board" | "map" | "orders" | "queue" | "exceptions" | "sla" | "ai" | "activity";

type Tone = "ok" | "warn" | "danger" | "neutral";

type KpiDef = {
  id: string;
  label: string;
  value: string;
  delta?: number | null;
  deltaSuffix?: string;
  tone: Tone;
  icon: React.ComponentType<{ className?: string }>;
  drill?: OpsDrillTarget;
};

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

function formatDelta(n: number | null | undefined, suffix = ""): string | null {
  if (n == null || n === 0) return null;
  const sign = n > 0 ? "+" : "";
  return `${sign}${n}${suffix}`;
}

function buildKpis(stats: OpsStats): KpiDef[] {
  const deltas = stats.deltas ?? {};
  const slaRisk = stats.sla_at_risk ?? 0;
  const slaBreached = stats.sla_breached ?? 0;
  const slaTotal = slaRisk + slaBreached;

  return [
    {
      id: "active",
      label: "Active",
      value: String(stats.active_deliveries),
      tone: "neutral",
      icon: Truck,
      drill: "board",
    },
    {
      id: "waiting",
      label: "Waiting dispatch",
      value: String(stats.waiting_dispatch),
      tone: stats.waiting_dispatch >= 15 ? "danger" : stats.waiting_dispatch >= 5 ? "warn" : "ok",
      icon: ClipboardList,
      drill: "queue",
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
      label: "SLA at risk",
      value: String(slaTotal),
      tone: slaBreached > 0 ? "danger" : slaRisk > 0 ? "warn" : "ok",
      icon: Timer,
      drill: "sla",
    },
    {
      id: "exceptions",
      label: "Exceptions",
      value: String(stats.open_exceptions),
      tone: stats.open_exceptions >= 5 ? "danger" : stats.open_exceptions > 0 ? "warn" : "ok",
      icon: AlertTriangle,
      drill: "exceptions",
    },
    {
      id: "revenue",
      label: "Revenue today",
      value: money(stats.revenue_today_cents),
      delta: deltas.revenue_today_cents,
      deltaSuffix: "",
      tone: "neutral",
      icon: Wallet,
    },
    {
      id: "completed",
      label: "Completed today",
      value: String(stats.completed_today),
      delta: deltas.completed_today,
      tone: "ok",
      icon: Boxes,
      drill: "orders",
    },
    {
      id: "orders",
      label: "Orders today",
      value: String(stats.orders_today),
      delta: deltas.orders_today,
      tone: "neutral",
      icon: Package,
      drill: "orders",
    },
  ];
}

function DeltaChip({ delta, isMoney }: { delta: number | null | undefined; isMoney?: boolean }) {
  if (delta == null || delta === 0) return null;
  const label = isMoney ? `${delta > 0 ? "+" : ""}${money(delta)}` : formatDelta(delta);
  if (!label) return null;
  const up = delta > 0;
  return (
    <span
      className={cn("text-[11px] font-medium", up ? "text-green-600" : "text-red-600")}
      title="vs yesterday"
    >
      {label} vs yd
    </span>
  );
}

export function KpiStrip({
  stats,
  onDrill,
}: {
  stats: OpsStats;
  onDrill?: (target: OpsDrillTarget) => void;
}) {
  const kpis = buildKpis(stats);

  return (
    <div className="ops-stat-grid grid grid-cols-2 gap-2 sm:grid-cols-4 xl:grid-cols-8">
      {kpis.map((k) => {
        const styles = TONE_STYLES[k.tone];
        const Icon = k.icon;
        const clickable = !!k.drill && !!onDrill;
        const Comp = clickable ? "button" : "div";
        return (
          <Comp
            key={k.id}
            type={clickable ? "button" : undefined}
            onClick={clickable ? () => onDrill?.(k.drill!) : undefined}
            title={clickable ? `Open ${k.label}` : undefined}
            className={cn(
              "rounded-xl border p-3 text-left transition-shadow",
              styles.ring,
              clickable &&
                "cursor-pointer hover:shadow-md focus:outline-none focus:ring-2 focus:ring-secondary/40"
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <p className="text-[11px] font-medium text-muted">{k.label}</p>
              <Icon className={cn("h-3.5 w-3.5", styles.icon)} />
            </div>
            <p className={cn("mt-1 text-lg font-bold tabular-nums", styles.value)}>{k.value}</p>
            <DeltaChip delta={k.delta} isMoney={k.id === "revenue"} />
          </Comp>
        );
      })}
    </div>
  );
}
