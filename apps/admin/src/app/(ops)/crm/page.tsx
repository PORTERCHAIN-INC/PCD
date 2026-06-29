"use client";

import { DataTable } from "@/components/DataTable";
import { useApiData } from "@/hooks/useApiData";
import { api } from "@/lib/api";
import { StatCard } from "@porterchain/ui/stat-card";

export default function CrmPage() {
  const { data: summary } = useApiData((t) => api.crmSummary(t));
  const { data: leads } = useApiData((t) => api.crmLeads(t));

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-primary">CRM</h1>
      {summary && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <StatCard label="Visitor Leads" value={String(summary.visitor_leads)} />
          <StatCard label="Quote Requests" value={String(summary.quote_requests)} />
          <StatCard label="Abandoned Checkouts" value={String(summary.abandoned_checkouts)} />
          <StatCard label="Business Inquiries" value={String(summary.business_inquiries)} />
          <StatCard label="Open Tasks" value={String(summary.open_tasks)} />
        </div>
      )}
      <DataTable
        columns={["Email", "Source", "Stage", "Created"]}
        rows={(leads || []).map((l) => [
          String(l.email),
          String(l.source),
          String(l.stage),
          String(l.created_at).slice(0, 10),
        ])}
      />
    </div>
  );
}
