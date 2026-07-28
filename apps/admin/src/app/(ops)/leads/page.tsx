"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { Badge, Button, Spinner } from "@/components/crm/primitives";
import { DRIVER_LEAD_SOURCE } from "@/lib/admin-nav";
import {
  LEAD_PRIORITIES,
  LEAD_STATUSES,
  leadsApi,
  leadForm,
  leadIntent,
  LEAD_SOURCES,
  PRIORITY_TONES,
  STATUS_TONES,
  type LeadFilters,
} from "@/lib/leads";

function formatWhen(iso: string): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function sourceLabel(source: string): string {
  if (source === DRIVER_LEAD_SOURCE) return "driver partner";
  return source.replace(/_/g, " ");
}

export default function LeadsPage() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const searchParams = useSearchParams();
  const sourceFromUrl = searchParams.get("source") ?? undefined;
  const isDriverInbox = sourceFromUrl === DRIVER_LEAD_SOURCE;
  const [filters, setFilters] = useState<LeadFilters>(() =>
    sourceFromUrl ? { source: sourceFromUrl } : {}
  );

  useEffect(() => {
    setFilters((f) => {
      if (f.source === sourceFromUrl) return f;
      return { ...f, source: sourceFromUrl };
    });
  }, [sourceFromUrl]);

  const {
    data: rows = [],
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["leads", JSON.stringify(filters)],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => leadsApi.list(await getApiToken(), filters),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary">
            {isDriverInbox ? "Driver Leads" : "Merchant Leads"}
          </h1>
          <p className="text-sm text-muted">
            {isDriverInbox
              ? "Vehicle partner applications from /vehicle-partner"
              : "Quotes, contact & business inquiries from the website"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {!isDriverInbox ? (
            <Link
              href="/leads/calendar"
              className="inline-flex items-center rounded-xl border border-primary/10 px-3 py-2 text-sm font-medium text-secondary hover:bg-slate-50"
            >
              Calendar
            </Link>
          ) : null}
          <Button variant="outline" onClick={() => void refetch()}>
            <RefreshCw className="h-4 w-4" /> Refresh
          </Button>
        </div>
      </div>

      <div className="rounded-2xl border border-primary/10 bg-white p-4">
        <div className="mb-4 flex flex-wrap gap-2">
          <input
            type="search"
            placeholder="Search name, email, company…"
            value={filters.search ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value || undefined }))}
            className="min-w-[220px] flex-1 rounded-xl border border-primary/10 px-3 py-2 text-sm"
          />
          <select
            value={filters.status ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value || undefined }))}
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
          >
            <option value="">All statuses</option>
            {LEAD_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, " ")}
              </option>
            ))}
          </select>
          <select
            value={filters.priority ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, priority: e.target.value || undefined }))}
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
          >
            <option value="">All priorities</option>
            {LEAD_PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <select
            value={filters.source ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, source: e.target.value || undefined }))}
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
          >
            <option value="">All sources</option>
            {LEAD_SOURCES.map((s) => (
              <option key={s} value={s}>
                {sourceLabel(s)}
              </option>
            ))}
          </select>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12">
            <Spinner />
          </div>
        ) : rows.length === 0 ? (
          <p className="py-12 text-center text-sm text-muted">
            {isDriverInbox ? "No driver partner leads yet." : "No merchant leads yet."}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-primary/10 text-xs uppercase tracking-wide text-muted">
                  <th className="px-3 py-2 font-medium">When</th>
                  <th className="px-3 py-2 font-medium">Contact</th>
                  <th className="px-3 py-2 font-medium">Source</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                  <th className="px-3 py-2 font-medium">Score</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((lead) => {
                  const intent = leadIntent(lead);
                  const form = leadForm(lead);
                  return (
                    <tr key={lead.id} className="border-b border-primary/5 hover:bg-secondary/5">
                      <td className="px-3 py-3 text-muted whitespace-nowrap">
                        {formatWhen(lead.created_at)}
                      </td>
                      <td className="px-3 py-3">
                        <Link
                          href={`/leads/${lead.id}`}
                          className="font-medium text-secondary hover:underline"
                        >
                          {lead.company_name}
                        </Link>
                        <p className="text-xs text-muted">
                          {lead.primary_contact_name ?? "—"}
                          {lead.email ? ` · ${lead.email}` : ""}
                        </p>
                        {intent && (
                          <p className="mt-0.5 text-xs capitalize text-primary/70">
                            Intent: {intent}
                          </p>
                        )}
                      </td>
                      <td className="px-3 py-3">
                        <span className="text-primary">{sourceLabel(lead.source)}</span>
                        {form && (
                          <p className="mt-0.5 text-xs text-muted capitalize">Form: {form}</p>
                        )}
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex flex-wrap gap-1">
                          <Badge tone={STATUS_TONES[lead.status] ?? "slate"}>{lead.status}</Badge>
                          <Badge tone={PRIORITY_TONES[lead.priority] ?? "slate"}>
                            {lead.priority}
                          </Badge>
                        </div>
                      </td>
                      <td
                        className={cn(
                          "px-3 py-3 font-mono",
                          lead.lead_score >= 30 && "font-semibold"
                        )}
                      >
                        {lead.lead_score}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
