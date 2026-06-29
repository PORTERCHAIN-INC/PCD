"use client";

import { DataTable } from "@/components/DataTable";
import { useApiData } from "@/hooks/useApiData";
import { api } from "@/lib/api";
import { formatCents } from "@porterchain/ui/utils";

export default function OrdersPage() {
  const { data } = useApiData((t) => api.orders(t));

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-primary">Order Management</h1>
      <DataTable
        columns={["Tracking", "State", "Amount", "Scheduled"]}
        rows={(data || []).map((o) => [
          String(o.tracking_number),
          String(o.state),
          formatCents(Number(o.amount_cents)),
          String(o.scheduled_at).slice(0, 16),
        ])}
      />
    </div>
  );
}
