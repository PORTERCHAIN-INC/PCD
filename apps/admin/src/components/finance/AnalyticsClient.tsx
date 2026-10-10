"use client";

import { useState } from "react";
import { formatCents } from "@porterchain/ui/utils";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useApiData } from "@/hooks/useApiData";
import { analyticsApi, type MarginGroup } from "@/lib/analytics";
import { Empty, FinanceShell, Section, Stat } from "./FinanceShell";

const pct = (v: number | null | undefined) => (v == null ? "—" : `${v.toFixed(1)}%`);
const money = (c: number | null | undefined) => (c == null ? "—" : formatCents(c));
const label = (k: string) => (k === "?" ? "Unknown" : k);
const th = "py-1 text-right font-medium";
const td = "py-1.5 text-right tabular-nums";

function GroupTable({ rows, head }: { rows: MarginGroup[]; head: string }) {
  if (!rows.length) return <Empty>No delivered stops yet.</Empty>;
  return (
    <table className="w-full text-sm">
      <thead className="text-left text-xs text-muted">
        <tr>
          <th className="py-1 font-medium">{head}</th>
          <th className={th}>Stops</th>
          <th className={th}>Revenue</th>
          <th className={th}>Margin</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-primary/5">
        {rows.slice(0, 8).map((r) => (
          <tr key={r.key}>
            <td className="max-w-[9rem] truncate py-1.5">{r.name ?? label(r.key)}</td>
            <td className={td}>{r.stops}</td>
            <td className={td}>{money(r.revenue_cents)}</td>
            <td className={`${td} ${(r.margin_pct ?? 100) < 15 ? "text-red-700" : ""}`}>
              {pct(r.margin_pct)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Trend({
  rows,
}: {
  rows: Array<{ day: string; revenue_cents: number; margin_cents: number }>;
}) {
  if (!rows.length) return <Empty>No revenue in this window.</Empty>;
  const max = Math.max(...rows.map((r) => r.revenue_cents), 1);
  return (
    <div className="flex h-28 items-end gap-[2px]" aria-label="Daily revenue and margin">
      {rows.map((r) => (
        <div
          key={r.day}
          title={`${r.day}: ${money(r.revenue_cents)} revenue, ${money(r.margin_cents)} margin`}
          className="relative flex-1 rounded-t bg-primary/15"
          style={{ height: `${(r.revenue_cents / max) * 100}%` }}
        >
          <div
            className="absolute bottom-0 w-full rounded-t bg-primary"
            style={{
              height: `${Math.max(0, r.margin_cents / Math.max(r.revenue_cents, 1)) * 100}%`,
            }}
          />
        </div>
      ))}
    </div>
  );
}

export default function AnalyticsClient() {
  const [days, setDays] = useState(30);
  const { data, loading } = useApiData((t) => analyticsApi.ops(t, days), [days], {
    key: `ops-analytics-${days}`,
  });
  const k = data?.kpis;

  return (
    <FinanceShell
      title="Analytics"
      subtitle="Cost, margin, service and demand — live from orders, routes and driver pay."
      primary={
        <select
          aria-label="Window"
          className="rounded-full border border-primary/15 bg-white px-4 py-2 text-sm font-semibold"
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
        >
          {[7, 30, 90].map((d) => (
            <option key={d} value={d}>
              Last {d} days
            </option>
          ))}
        </select>
      }
    >
      {loading && !data ? (
        <PageSkeleton rows={3} />
      ) : !data || !k ? (
        <Empty>Analytics unavailable.</Empty>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
            <Stat label="Revenue" value={money(k.revenue_cents)} />
            <Stat
              label="Margin"
              value={pct(k.margin_pct)}
              tone={(k.margin_pct ?? 0) < 15 ? "bad" : "good"}
            />
            <Stat label="Cost / stop" value={money(k.cost_per_stop_cents)} />
            <Stat
              label="On-time"
              value={pct(k.on_time_pct)}
              tone={(k.on_time_pct ?? 100) < 95 ? "bad" : "good"}
            />
            <Stat label="Fill" value={pct(k.fill_pct)} />
            <Stat label="Stops" value={String(k.delivered_stops)} />
            <Stat label="Routes" value={String(k.routes)} />
            <Stat
              label="Failed"
              value={`${k.failed} · ${pct(k.failed_pct)}`}
              tone={(k.failed_pct ?? 0) > 3 ? "bad" : undefined}
            />
          </div>
          {k.estimated_cost_share > 0.5 && (
            <p className="text-xs text-muted">
              {Math.round(k.estimated_cost_share * 100)}% of driver cost is estimated from the pay
              plan (no wallet credit recorded yet).
            </p>
          )}

          <Section
            title="Revenue trend"
            aside={<span className="text-xs text-muted">dark = margin</span>}
          >
            <Trend rows={data.trend} />
          </Section>

          <div className="grid gap-4 lg:grid-cols-3">
            <Section title="Margin by merchant">
              <GroupTable rows={data.margin_by.merchant} head="Merchant" />
            </Section>
            <Section title="Margin by FSA">
              <GroupTable rows={data.margin_by.fsa} head="FSA" />
            </Section>
            <Section title="Margin by vehicle">
              <GroupTable rows={data.margin_by.vehicle} head="Vehicle" />
            </Section>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Section title="Driver productivity">
              {data.drivers.length ? (
                <table className="w-full text-sm">
                  <thead className="text-left text-xs text-muted">
                    <tr>
                      <th className="py-1 font-medium">Driver</th>
                      <th className={th}>Routes</th>
                      <th className={th}>Stops/route</th>
                      <th className={th}>Revenue</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-primary/5">
                    {data.drivers.slice(0, 8).map((d) => (
                      <tr key={d.driver_id}>
                        <td className="py-1.5">{d.name ?? d.driver_id.slice(0, 8)}</td>
                        <td className={td}>{d.routes}</td>
                        <td className={td}>{d.stops_per_route}</td>
                        <td className={td}>{money(d.revenue_cents)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <Empty>No routes yet.</Empty>
              )}
            </Section>
            <Section
              title="Demand forecast · next 7 days"
              aside={<span className="text-xs text-muted">weekday avg, 6 weeks</span>}
            >
              {data.forecast.length ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="text-left text-xs text-muted">
                      <tr>
                        <th className="py-1 font-medium">FSA</th>
                        {data.forecast[0].days.map((d) => (
                          <th key={d.day} className={th}>
                            {new Date(`${d.day}T12:00:00`).toLocaleDateString("en-CA", {
                              weekday: "short",
                            })}
                          </th>
                        ))}
                        <th className={th}>7d</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-primary/5">
                      {data.forecast.map((f) => (
                        <tr key={f.fsa}>
                          <td className="py-1.5">{label(f.fsa)}</td>
                          {f.days.map((d) => (
                            <td key={d.day} className={td}>
                              {d.expected}
                            </td>
                          ))}
                          <td className={`${td} font-semibold`}>{f.next7_total}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <Empty>Not enough history yet.</Empty>
              )}
            </Section>
          </div>
        </div>
      )}
    </FinanceShell>
  );
}
