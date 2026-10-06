"use client";

import { useApiData } from "@/hooks/useApiData";
import { leadsApi } from "@/lib/leads";
import { PageSkeleton } from "@porterchain/ui/loading";
import { SettingsCard } from "../ui/SettingsPrimitives";

/** Static CrmLead processing inventory — not a multi-region residency product. */
export function LeadRopaCard() {
  const { data, error, refetch } = useApiData((t) => leadsApi.privacyRopa(t), [], {
    key: "lead-ropa",
  });

  return (
    <SettingsCard title="Lead processing record (RoPA)">
      <p className="mb-3 text-xs text-muted">
        Article 30 / PIPEDA-style inventory for CrmLead. Primary residency Canada (Ontario). Cookie
        CMP consent is separate from lead.consent.
      </p>
      {error ? <p className="mb-2 text-sm text-red-600">{error}</p> : null}
      {data ? (
        <>
          <dl className="mb-3 grid gap-1 text-xs text-muted sm:grid-cols-2">
            <div>
              <dt className="inline font-medium text-primary">Controller · </dt>
              <dd className="inline">{data.controller}</dd>
            </div>
            <div>
              <dt className="inline font-medium text-primary">Residency · </dt>
              <dd className="inline">{data.primary_residency}</dd>
            </div>
            <div>
              <dt className="inline font-medium text-primary">Multi-region · </dt>
              <dd className="inline">{data.multi_region ? "yes" : "no"}</dd>
            </div>
            <div>
              <dt className="inline font-medium text-primary">Contact · </dt>
              <dd className="inline">{data.contact}</dd>
            </div>
          </dl>
          <ul
            className="max-h-72 space-y-2 overflow-y-auto text-sm"
            aria-label="Processing activities"
          >
            {data.activities.map((a) => (
              <li key={a.activity} className="rounded-lg border border-primary/10 px-3 py-2">
                <p className="font-medium text-primary">{a.activity.replace(/_/g, " ")}</p>
                <p className="text-xs text-muted">{a.purpose}</p>
                <p className="mt-1 text-xs text-muted">
                  Bases: {a.legal_bases.join(", ")} · Retention: {a.retention}
                </p>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-muted">{data.notes}</p>
        </>
      ) : (
        <PageSkeleton rows={2} />
      )}
      <button
        type="button"
        className="mt-3 text-xs font-medium text-secondary hover:underline"
        onClick={() => void refetch()}
      >
        Refresh
      </button>
    </SettingsCard>
  );
}
