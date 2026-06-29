"use client";

import { DataTable } from "@/components/DataTable";
import { useApiData } from "@/hooks/useApiData";
import { api } from "@/lib/api";

export default function SupportPage() {
  const { data } = useApiData((t) => api.tickets(t));

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-primary">Customer Support</h1>
      <DataTable
        columns={["Subject", "Priority", "Status", "Created"]}
        rows={(data || []).map((t) => [
          String(t.subject),
          String(t.priority),
          String(t.status),
          String(t.created_at).slice(0, 10),
        ])}
      />
    </div>
  );
}
