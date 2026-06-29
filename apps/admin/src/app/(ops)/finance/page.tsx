"use client";

import { useApiData } from "@/hooks/useApiData";
import { api } from "@/lib/api";
import { StatCard } from "@porterchain/ui/stat-card";
import { formatCents } from "@porterchain/ui/utils";

export default function FinancePage() {
  const { data } = useApiData((t) => api.financeSummary(t));

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-primary">Finance</h1>
      {data && (
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard label="Monthly Revenue" value={formatCents(data.monthly_revenue_cents)} />
          <StatCard label="Invoiced" value={formatCents(data.invoice_total_cents)} />
          <StatCard label="Refunds" value={String(data.refund_count)} />
        </div>
      )}
    </div>
  );
}
