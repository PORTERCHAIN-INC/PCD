"use client";

import { type StatementDetail } from "@/lib/billing";
import { formatCents } from "@/lib/utils";
import { Kpi, StatusBadge } from "./shared";

export function StatementTab({ statement }: { statement: StatementDetail }) {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        <Kpi label="Period orders" value={String(statement.monthly_orders)} />
        <Kpi label="Period spend" value={formatCents(statement.monthly_spend_cents)} />
        <Kpi label="Line items total" value={formatCents(statement.line_items_total_cents)} />
      </div>
      <div className="ops-table-scroll rounded-2xl border border-primary/10 bg-white">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-primary/10 text-muted">
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Reference</th>
              <th className="px-4 py-3">Description</th>
              <th className="px-4 py-3">Amount</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {statement.line_items.map((line, i) => (
              <tr key={i} className="border-b border-primary/5">
                <td className="px-4 py-3 capitalize">{String(line.type)}</td>
                <td className="px-4 py-3 font-mono text-xs">{String(line.reference ?? "—")}</td>
                <td className="px-4 py-3">{String(line.description ?? "")}</td>
                <td className="px-4 py-3">{formatCents(Number(line.amount_cents) || 0)}</td>
                <td className="px-4 py-3">
                  {line.status ? <StatusBadge status={String(line.status)} /> : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
