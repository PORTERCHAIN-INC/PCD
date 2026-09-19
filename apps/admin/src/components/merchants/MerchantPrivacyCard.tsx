"use client";

import { useApiData } from "@/hooks/useApiData";
import { merchants, type MerchantPrivacyFile } from "@/lib/merchants";
import { Badge, SectionCard } from "@/components/crm/primitives";
import { dateTime } from "@/lib/crmFormat";

function toneFor(status: MerchantPrivacyFile["status"]): string {
  if (status === "pending") return "amber";
  if (status === "erased") return "slate";
  return "green";
}

function statusLabel(status: MerchantPrivacyFile["status"]): string {
  if (status === "pending") return "Deletion requested";
  if (status === "erased") return "Erased";
  return "No request";
}

export default function MerchantPrivacyCard({
  id,
  compact = false,
}: {
  id: string;
  compact?: boolean;
}) {
  const { data, error } = useApiData((t) => merchants.privacy(t, id), [id], {
    key: `merchant-privacy-${id}`,
  });

  if (compact) {
    if (error || !data) return null;
    if (data.status === "none") return null;
    return (
      <SectionCard title="Privacy request">
        <div className="space-y-2 px-5 py-4 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={toneFor(data.status)}>{statusLabel(data.status)}</Badge>
            {data.delete_reference ? (
              <span className="font-mono text-xs text-primary">{data.delete_reference}</span>
            ) : null}
          </div>
          <p className="text-muted">{data.message}</p>
          {data.status === "pending" ? (
            <p className="text-amber-900">
              Close this company on Settings, then erase contact details. Order numbers and invoice
              amounts stay.
            </p>
          ) : null}
        </div>
      </SectionCard>
    );
  }

  return (
    <SectionCard title="Privacy">
      {error ? <p className="px-5 py-4 text-sm text-red-600">{error}</p> : null}
      {data ? (
        <div className="space-y-3 px-5 py-4 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={toneFor(data.status)}>{statusLabel(data.status)}</Badge>
            {data.delete_reference ? (
              <span className="font-mono text-xs text-primary">{data.delete_reference}</span>
            ) : null}
          </div>
          <p className="text-muted">{data.message}</p>
          {data.delete_requested_at ? (
            <p className="text-xs text-muted">Requested {dateTime(data.delete_requested_at)}</p>
          ) : null}
          {data.erased_at ? (
            <p className="text-xs text-muted">Erased {dateTime(data.erased_at)}</p>
          ) : null}
          {data.status === "pending" ? (
            <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-amber-900">
              Close this company first, then use Execute privacy erasure. Live orders and unpaid
              invoices block erasure.
            </p>
          ) : null}
          {(data.recent_logs?.length ?? 0) > 0 ? (
            <ul className="divide-y divide-primary/5 border-t border-primary/10 pt-2">
              {data.recent_logs?.slice(0, 12).map((row) => (
                <li key={row.id} className="flex justify-between gap-3 py-2">
                  <span className="font-medium text-primary">{row.summary}</span>
                  <span className="shrink-0 text-xs text-muted">{dateTime(row.created_at)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-muted">No company activity logged yet.</p>
          )}
        </div>
      ) : null}
    </SectionCard>
  );
}
