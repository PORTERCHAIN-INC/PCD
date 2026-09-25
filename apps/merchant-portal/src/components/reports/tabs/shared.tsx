"use client";

import type { ExecutiveReport } from "@/lib/reports";
import { formatPercent } from "@/lib/reports";
import { formatCents } from "@/lib/utils";

export function Metric({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-2xl border border-primary/10 bg-white p-5">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-2 text-2xl font-bold text-primary">{value}</p>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}

export function RankedList({
  title,
  empty,
  rows,
}: {
  title: string;
  empty: string;
  rows: Array<{ label: string; count: number }>;
}) {
  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">{title}</h2>
      <ul className="mt-4 space-y-2 text-sm">
        {rows.length === 0 && <li className="text-muted">{empty}</li>}
        {rows.map((r) => (
          <li key={r.label} className="flex justify-between gap-4">
            <span className="truncate text-muted">{r.label}</span>
            <span className="font-medium">{r.count}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function KeyValueList({
  title,
  items,
  empty,
}: {
  title: string;
  items: [string, number][];
  empty: string;
}) {
  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">{title}</h2>
      <ul className="mt-4 space-y-2 text-sm">
        {items.length === 0 && <li className="text-muted">{empty}</li>}
        {items.map(([k, v]) => (
          <li key={k} className="flex justify-between gap-4">
            <span className="text-muted">{k}</span>
            <span className="font-medium">{v}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
export function KpiGrid({ kpis }: { kpis: ExecutiveReport["kpis"] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      {kpis.map((kpi) => (
        <div key={kpi.label} className="rounded-2xl border border-primary/10 bg-white p-5">
          <p className="text-sm text-muted">{kpi.label}</p>
          <p className="mt-2 text-2xl font-bold text-primary">
            {kpi.format === "currency"
              ? kpi.value == null
                ? "—"
                : formatCents(kpi.value)
              : kpi.format === "percent"
                ? formatPercent(kpi.value)
                : kpi.value == null
                  ? "—"
                  : kpi.value}
          </p>
        </div>
      ))}
    </div>
  );
}
