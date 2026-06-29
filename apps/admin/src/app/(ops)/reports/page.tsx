"use client";

import { useApiData } from "@/hooks/useApiData";
import { api } from "@/lib/api";
import { StatCard } from "@porterchain/ui/stat-card";
import { formatCents } from "@porterchain/ui/utils";

export default function ReportsPage() {
  const { data } = useApiData((t) => api.reports(t));

  if (!data) return <p className="text-muted">Loading reports…</p>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-primary">Reports</h1>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard label="Monthly Orders" value={String(data.monthly_orders)} />
        <StatCard label="Revenue" value={formatCents(Number(data.monthly_revenue_cents))} />
        <StatCard label="Active Merchants" value={String(data.active_merchants)} />
        <StatCard label="Active Drivers" value={String(data.active_drivers)} />
        <StatCard label="Delivery SLA" value={`${data.delivery_sla_percent}%`} />
        <StatCard label="Cancellation Rate" value={`${data.cancellation_rate_percent}%`} />
        <StatCard label="Claim Rate" value={`${data.claim_rate_percent}%`} />
      </div>
    </div>
  );
}
