"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, RefreshCw } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { Badge, Button } from "@/components/crm/primitives";
import { leadsApi } from "@/lib/leads";
import AdminPage from "@/components/layout/AdminPage";
import { EmptyState, InboxSkeleton } from "@/components/leads/LeadDeskBits";
import { scoreTone } from "@/components/leads/LeadRow";

function money(cents: number): string {
  return (cents / 100).toLocaleString(undefined, {
    style: "currency",
    currency: "CAD",
    maximumFractionDigits: 0,
  });
}

export default function LeadsPipelineClient() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const [search, setSearch] = useState("");

  const {
    data: columns = [],
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["leads-pipeline", search],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => leadsApi.pipeline(await getApiToken(), { search: search || undefined }),
  });

  return (
    <AdminPage>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <Link
            href="/leads"
            className="mb-2 inline-flex items-center gap-2 text-sm text-secondary"
          >
            <ArrowLeft className="h-4 w-4" /> Back to inbox
          </Link>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-secondary">Sales</p>
          <h1 className="text-3xl font-extrabold tracking-tight text-primary">Pipeline</h1>
          <p className="text-sm text-slate-600">Leads and deals by stage, highest score first</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="search"
            placeholder="Search…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="rounded-full border border-primary/15 px-4 py-2 text-sm"
          />
          <Button variant="outline" onClick={() => void refetch()}>
            <RefreshCw className="h-4 w-4" /> Refresh
          </Button>
        </div>
      </div>

      {isLoading ? (
        <InboxSkeleton />
      ) : columns.every((c) => c.count === 0) ? (
        <EmptyState title="Pipeline is empty" hint="Leads appear here as soon as they arrive; reply or quote to move them along." />
      ) : (
        <div className="mt-6 flex snap-x gap-3 overflow-x-auto pb-4">
          {columns.map((col) => (
            <div
              key={col.stage}
              className="w-[85vw] shrink-0 snap-start rounded-3xl border border-primary/10 bg-slate-50 p-3 sm:w-72"
            >
              <div className="mb-3 flex items-baseline justify-between gap-2">
                <h2 className="text-sm font-bold capitalize text-primary">
                  {col.stage.replace(/_/g, " ")}
                </h2>
                <span className="text-xs text-muted">{col.count}</span>
              </div>
              <p className="mb-3 text-xs text-muted">{money(col.value_cents)}</p>
              <ul className="space-y-2">
                {col.cards.map((card) => (
                  <li
                    key={`${card.type}-${card.id}`}
                    className="rounded-xl border border-primary/10 bg-white p-3 shadow-sm"
                  >
                    <Link
                      href={card.type === "lead" ? `/leads/${card.id}` : `/leads`}
                      className={cn(
                        "block text-sm font-medium hover:underline",
                        card.sla_breached ? "text-red-800" : "text-secondary"
                      )}
                    >
                      {card.title}
                    </Link>
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      <Badge tone="slate">{card.type}</Badge>
                      {card.channel ? (
                        <Badge tone="slate">{card.channel.replace(/_/g, " ")}</Badge>
                      ) : null}
                      {card.has_draft ? <Badge tone="violet">draft</Badge> : null}
                      {card.nurture ? <Badge tone="teal">nurture</Badge> : null}
                      {card.sla_breached ? <Badge tone="red">SLA</Badge> : null}
                    </div>
                    {card.type === "lead" && typeof card.score === "number" ? (
                      <p className={cn("mt-1 text-lg font-extrabold tabular-nums", scoreTone(card.score))}>
                        {card.score}
                      </p>
                    ) : card.secondary ? (
                      <p className="mt-1 text-xs text-slate-600">{card.secondary}</p>
                    ) : null}
                    {card.value_cents ? (
                      <p className="mt-0.5 text-xs text-muted">{money(card.value_cents)}</p>
                    ) : null}
                  </li>
                ))}
                {col.hidden > 0 ? (
                  <li className="text-xs text-muted">+{col.hidden} more leads</li>
                ) : null}
              </ul>
            </div>
          ))}
        </div>
      )}
    </AdminPage>
  );
}
