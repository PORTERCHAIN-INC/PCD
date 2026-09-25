"use client";

import type { ClaimsSummary } from "@/lib/reports";
import { formatCents } from "@/lib/utils";
import { KeyValueList, Metric } from "./shared";

export function ClaimsTab({ data }: { data: ClaimsSummary }) {
  const byType = Object.entries(data.by_type);
  const byStatus = Object.entries(data.by_status);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <Metric label="Total claims" value={String(data.total_claims)} />
        <Metric label="Open claims" value={String(data.open_claims)} />
        <Metric label="Compensation" value={formatCents(data.compensation_cost_cents)} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <KeyValueList title="By type" items={byType} empty="No claims" />
        <KeyValueList title="By status" items={byStatus} empty="No claims" />
      </div>
    </div>
  );
}
