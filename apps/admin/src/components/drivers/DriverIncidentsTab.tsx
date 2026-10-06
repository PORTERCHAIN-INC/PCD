"use client";

import { useApiData } from "@/hooks/useApiData";
import { PageSkeleton } from "@porterchain/ui/loading";
import { drivers } from "@/lib/drivers";
import { Badge, SectionCard } from "@/components/crm/primitives";
import { shortDate, titleCase } from "@/lib/crmFormat";

export function IncidentsTab({ id }: { id: string }) {
  const { data, error } = useApiData((t) => drivers.incidents(t, id), [id], {
    key: `driver-incidents-${id}`,
  });
  if (!data && !error) return <PageSkeleton rows={3} />;
  const incidents = data?.incidents ?? [];
  const claims = data?.claims ?? [];
  return (
    <div className="space-y-5">
      {error && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
      <div className="grid gap-5 md:grid-cols-2">
        <SectionCard title={`Incidents (${incidents.length})`}>
          <div className="divide-y divide-primary/5">
            {incidents.map((i) => (
              <div key={i.id} className="flex items-center justify-between px-5 py-3">
                <div>
                  <p className="text-sm font-medium text-primary">{titleCase(i.type)}</p>
                  <p className="text-xs text-muted">{shortDate(i.created_at)}</p>
                </div>
                <Badge tone={i.status === "resolved" ? "green" : "amber"}>
                  {titleCase(i.status)}
                </Badge>
              </div>
            ))}
            {incidents.length === 0 && (
              <p className="px-5 py-10 text-center text-sm text-muted">No incidents on record.</p>
            )}
          </div>
        </SectionCard>
        <SectionCard title={`Claims (${claims.length})`}>
          <div className="divide-y divide-primary/5">
            {claims.map((c) => (
              <div key={c.id} className="flex items-center justify-between px-5 py-3">
                <div>
                  <p className="text-sm font-medium text-primary">{titleCase(c.claim_type)}</p>
                  <p className="text-xs text-muted">{shortDate(c.created_at)}</p>
                </div>
                <Badge tone={c.status === "resolved" ? "green" : "amber"}>
                  {titleCase(c.status)}
                </Badge>
              </div>
            ))}
            {claims.length === 0 && (
              <p className="px-5 py-10 text-center text-sm text-muted">No claims.</p>
            )}
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
