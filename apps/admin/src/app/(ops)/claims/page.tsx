"use client";

import { DataTable } from "@/components/DataTable";
import { useApiData } from "@/hooks/useApiData";
import { api } from "@/lib/api";

export default function ClaimsPage() {
  const { data } = useApiData((t) => api.claims(t));

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-primary">Claims & Incidents</h1>
      <DataTable
        columns={["Type", "Order", "Status", "Created"]}
        rows={(data || []).map((c) => [
          String(c.claim_type),
          String(c.order_id).slice(0, 8),
          String(c.status),
          String(c.created_at).slice(0, 10),
        ])}
      />
    </div>
  );
}
