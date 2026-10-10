"use client";

import { useApiData } from "@/hooks/useApiData";
import { dispatch, money, type DispatchMetrics } from "@/lib/dispatch";

type Tile = { label: string; value: string; hint: string };

function tiles(m: DispatchMetrics | null): Tile[] {
  const pct = (v: number | null | undefined) => (v == null ? "—" : `${Math.round(v)}%`);
  return [
    {
      label: "Order → dispatch",
      value: m?.order_to_dispatch_min == null ? "—" : `${Math.round(m.order_to_dispatch_min)}m`,
      hint: "median minutes to a driver",
    },
    { label: "On time", value: pct(m?.on_time_pct), hint: "delivered by promise" },
    { label: "First attempt", value: pct(m?.first_attempt_pct), hint: "no failed attempt" },
    { label: "Cost / stop", value: money(m?.cost_per_stop_cents), hint: "driver pay plan ÷ stops" },
    { label: "Fill", value: pct(m?.fill_pct), hint: "load vs vehicle" },
    {
      label: "Stops / hr",
      value: m?.stops_per_driver_hour == null ? "—" : m.stops_per_driver_hour.toFixed(1),
      hint: "per driver-hour",
    },
  ];
}

export function MetricsBar({ tick, days = 7 }: { tick: number; days?: number }) {
  const { data } = useApiData((t) => dispatch.metrics(t, days), [tick, days], {
    key: "dispatch-metrics",
  });
  return (
    <section
      aria-label="Speed metrics"
      className="grid grid-cols-2 gap-px overflow-hidden rounded-2xl bg-white/10 sm:grid-cols-3 lg:grid-cols-6"
      style={{ backgroundColor: "var(--primary)" }}
    >
      {tiles(data).map((t) => (
        <div key={t.label} className="px-4 py-3" style={{ backgroundColor: "var(--primary)" }}>
          <p className="text-[11px] font-medium uppercase tracking-wider text-white/70">{t.label}</p>
          <p className="mt-0.5 text-2xl font-semibold tabular-nums text-white">{t.value}</p>
          <p className="text-[11px] text-white/60">{t.hint}</p>
        </div>
      ))}
    </section>
  );
}
