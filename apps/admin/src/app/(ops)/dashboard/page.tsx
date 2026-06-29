"use client";

import { useApiData } from "@/hooks/useApiData";
import { api } from "@/lib/api";
import { StatCard } from "@porterchain/ui/stat-card";
import { formatCents } from "@porterchain/ui/utils";

export default function DashboardPage() {
  const { data, error } = useApiData((t) => api.dashboard(t));

  if (error) return <p className="text-red-600">{error}</p>;
  if (!data) return <p className="text-muted">Loading dashboard…</p>;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-primary">Operations Dashboard</h1>
        <p className="text-sm text-muted">Real-time Porterchain platform overview</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Today's Revenue" value={formatCents(data.todays_revenue_cents)} />
        <StatCard label="Today's Bookings" value={String(data.todays_bookings)} />
        <StatCard label="Pending Quotes" value={String(data.pending_quotes)} />
        <StatCard label="Merchant Approvals" value={String(data.pending_merchant_approvals)} />
        <StatCard label="Drivers Online" value={String(data.drivers_online)} />
        <StatCard label="Drivers Offline" value={String(data.drivers_offline)} />
        <StatCard label="Awaiting Dispatch" value={String(data.orders_waiting_dispatch)} />
        <StatCard label="In Transit" value={String(data.orders_in_transit)} />
        <StatCard label="Completed Today" value={String(data.completed_today)} />
        <StatCard label="Failed Deliveries" value={String(data.failed_deliveries)} />
        <StatCard label="Open Claims" value={String(data.open_claims)} />
        <StatCard
          label="Outstanding Invoices"
          value={formatCents(data.outstanding_invoices_cents)}
        />
        <StatCard label="Support Tickets" value={String(data.open_support_tickets)} />
        <StatCard label="Fleet Health" value={`${data.fleet_health_percent}%`} />
      </div>
    </div>
  );
}
