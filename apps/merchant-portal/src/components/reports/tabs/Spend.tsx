"use client";

import { formatCents } from "@/lib/utils";

export function SpendAttribution({
  byChannel,
  byModel,
  topBands,
}: {
  byChannel?: Array<{ channel: string; orders: number; spend_cents: number }>;
  byModel?: Array<{ pricing_model: string; orders: number; spend_cents: number }>;
  topBands?: Array<{ band: string; pricing_model: string; orders: number; spend_cents: number }>;
}) {
  if (!byChannel?.length && !byModel?.length && !topBands?.length) return null;
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <SpendTable
        title="Spend by channel"
        empty="No channel spend this period"
        rows={(byChannel ?? []).map((r) => ({
          label: r.channel,
          orders: r.orders,
          spend_cents: r.spend_cents,
        }))}
      />
      <SpendTable
        title="Spend by pricing model"
        empty="No pricing-model spend"
        rows={(byModel ?? []).map((r) => ({
          label: r.pricing_model.toUpperCase(),
          orders: r.orders,
          spend_cents: r.spend_cents,
        }))}
      />
      <SpendTable
        title="Top bands"
        empty="No band data yet"
        rows={(topBands ?? []).map((r) => ({
          label: r.band,
          orders: r.orders,
          spend_cents: r.spend_cents,
        }))}
      />
    </div>
  );
}

export function SpendTable({
  title,
  empty,
  rows,
}: {
  title: string;
  empty: string;
  rows: Array<{ label: string; orders: number; spend_cents: number }>;
}) {
  return (
    <section className="overflow-hidden rounded-2xl border border-primary/10 bg-white">
      <div className="border-b border-primary/10 px-4 py-3">
        <h2 className="font-semibold text-primary">{title}</h2>
      </div>
      {rows.length === 0 ? (
        <p className="px-4 py-6 text-sm text-muted">{empty}</p>
      ) : (
        <table className="w-full text-sm">
          <thead className="border-b border-primary/5 text-left text-muted">
            <tr>
              <th className="px-4 py-2 font-medium">Slice</th>
              <th className="px-4 py-2 font-medium">Orders</th>
              <th className="px-4 py-2 font-medium text-right">Spend</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label} className="border-b border-primary/5">
                <td className="px-4 py-2 capitalize">{row.label}</td>
                <td className="px-4 py-2">{row.orders}</td>
                <td className="px-4 py-2 text-right font-medium">{formatCents(row.spend_cents)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
