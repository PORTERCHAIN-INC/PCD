"use client";

import { SpendPerformanceChart } from "@/components/dashboard/PerformanceChart";
import type { ReportsOverview } from "@/lib/reports";
import { formatCents } from "@/lib/utils";
import { Metric } from "./shared";
import { SpendAttribution } from "./Spend";

export function InvoicesTab({ data }: { data: ReportsOverview["invoice_reports"] }) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <Metric label="Invoices" value={String(data.invoice_count)} />
        <Metric label="Total" value={formatCents(data.invoice_total_cents)} />
        <Metric label="Tax" value={formatCents(data.tax_cents)} />
      </div>
      <SpendAttribution
        byChannel={data.spend_by_channel}
        byModel={data.spend_by_pricing_model}
        topBands={data.top_pricing_bands}
      />
      <section className="overflow-hidden rounded-2xl border border-primary/10 bg-white">
        <table className="w-full text-sm">
          <thead className="border-b border-primary/10 bg-primary/5 text-left text-muted">
            <tr>
              <th className="px-4 py-3 font-medium">Invoice</th>
              <th className="px-4 py-3 font-medium">Order</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium text-right">Amount</th>
            </tr>
          </thead>
          <tbody>
            {data.invoices.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-muted">
                  No invoices this period
                </td>
              </tr>
            )}
            {data.invoices.map((inv) => (
              <tr key={String(inv.invoice_id)} className="border-b border-primary/5">
                <td className="px-4 py-3">{String(inv.invoice_number ?? "—")}</td>
                <td className="px-4 py-3 text-muted">{String(inv.order_number ?? "—")}</td>
                <td className="px-4 py-3">{String(inv.status ?? "—")}</td>
                <td className="px-4 py-3 text-right font-medium">
                  {formatCents(Number(inv.amount_cents ?? 0))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
