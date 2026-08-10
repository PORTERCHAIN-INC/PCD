"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, RefreshCw, X } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import SupportGrid from "@/components/support/SupportGrid";
import { Button, Spinner } from "@/components/crm/primitives";
import {
  TICKET_CATEGORIES,
  TICKET_PRIORITIES,
  TICKET_STATUSES,
  supportApi,
  type SupportFilters,
} from "@/lib/support";

type ModuleTab =
  | "dashboard"
  | "tickets"
  | "customers"
  | "merchants"
  | "drivers"
  | "internal"
  | "operations"
  | "claims"
  | "finance"
  | "technical"
  | "kb"
  | "macros"
  | "automation"
  | "reports"
  | "settings";

const MODULE_TABS: { id: ModuleTab; label: string; module?: string }[] = [
  { id: "dashboard", label: "Dashboard" },
  { id: "tickets", label: "Tickets" },
  { id: "customers", label: "Customers" },
  { id: "merchants", label: "Merchants" },
  { id: "drivers", label: "Drivers" },
  { id: "internal", label: "Internal Requests", module: "internal" },
  { id: "operations", label: "Operations", module: "operations" },
  { id: "claims", label: "Claims", module: "claims" },
  { id: "finance", label: "Finance Issues", module: "finance" },
  { id: "technical", label: "Technical Issues", module: "technical" },
  { id: "kb", label: "Knowledge Base" },
  { id: "macros", label: "Macros" },
  { id: "automation", label: "Automation" },
  { id: "reports", label: "Reports" },
  { id: "settings", label: "Settings" },
];

export default function SupportPage() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const searchParams = useSearchParams();
  const qc = useQueryClient();
  const [tab, setTab] = useState<ModuleTab>("tickets");
  const [filters, setFilters] = useState<SupportFilters>({});
  const [selected, setSelected] = useState<string[]>([]);
  const enabled = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");
  const filterKey = JSON.stringify({ ...filters, tab });

  useEffect(() => {
    const customerId = searchParams.get("customer_id");
    const merchantId = searchParams.get("merchant_id");
    if (!customerId && !merchantId) return;
    setTab("tickets");
    setFilters((f) => ({
      ...f,
      ...(customerId ? { customer_id: customerId } : {}),
      ...(merchantId ? { merchant_id: merchantId } : {}),
    }));
  }, [searchParams]);

  const activeModule = MODULE_TABS.find((t) => t.id === tab)?.module;
  const listFilters: SupportFilters = {
    ...filters,
    module: activeModule,
  };

  const {
    data: rows = [],
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["support-tickets", filterKey],
    enabled:
      enabled &&
      tab !== "dashboard" &&
      tab !== "kb" &&
      tab !== "macros" &&
      tab !== "automation" &&
      tab !== "reports" &&
      tab !== "settings",
    queryFn: async () => supportApi.list(await getApiToken(), listFilters),
  });

  const { data: dashboard } = useQuery({
    queryKey: ["support-dashboard"],
    enabled,
    queryFn: async () => supportApi.dashboard(await getApiToken()),
  });

  const { data: reports } = useQuery({
    queryKey: ["support-reports"],
    enabled: enabled && tab === "reports",
    queryFn: async () => supportApi.reports(await getApiToken()),
  });

  const { data: kb } = useQuery({
    queryKey: ["support-kb"],
    enabled: enabled && tab === "kb",
    queryFn: async () => supportApi.knowledgeBase(await getApiToken()),
  });

  const { data: macros = [] } = useQuery({
    queryKey: ["support-macros"],
    enabled: enabled && tab === "macros",
    queryFn: async () => supportApi.macros(await getApiToken()),
  });

  const { data: automation } = useQuery({
    queryKey: ["support-automation"],
    enabled: enabled && tab === "automation",
    queryFn: async () => supportApi.automation(await getApiToken()),
  });

  const { data: slaConfig } = useQuery({
    queryKey: ["support-sla"],
    enabled: enabled && tab === "settings",
    queryFn: async () => supportApi.slaConfig(await getApiToken()),
  });

  async function createTicket() {
    const subject = prompt("Subject");
    const category = prompt(`Category:\n${TICKET_CATEGORIES.slice(0, 8).join("\n")}…`);
    if (!subject) return;
    const token = await getApiToken();
    await supportApi.create(token, { subject, category: category || "general_inquiry" });
    await qc.invalidateQueries({ queryKey: ["support-tickets"] });
    await qc.invalidateQueries({ queryKey: ["support-dashboard"] });
    void refetch();
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary">Support Center</h1>
          <p className="text-sm text-muted">
            Enterprise customer, merchant, driver and operations support platform
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => void refetch()}>
            <RefreshCw className="h-4 w-4" /> Refresh
          </Button>
          <Button variant="primary" onClick={() => void createTicket()}>
            <Plus className="h-4 w-4" /> New ticket
          </Button>
        </div>
      </div>

      <nav className="flex gap-1 overflow-x-auto border-b border-primary/10 pb-px">
        {MODULE_TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={cn(
              "shrink-0 rounded-t-lg px-3 py-2 text-sm font-medium",
              tab === t.id
                ? "border border-b-0 border-primary/10 bg-white text-secondary"
                : "text-muted"
            )}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "dashboard" && dashboard && (
        <div className="space-y-6">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
            <Kpi label="Open tickets" value={dashboard.open_tickets} />
            <Kpi
              label="Urgent"
              value={dashboard.urgent_tickets}
              alert={dashboard.urgent_tickets > 0}
            />
            <Kpi
              label="SLA breaches"
              value={dashboard.sla_breaches}
              alert={dashboard.sla_breaches > 0}
            />
            <Kpi label="Pending customer" value={dashboard.pending_customer} />
            <Kpi label="Pending merchant" value={dashboard.pending_merchant} />
            <Kpi label="Pending driver" value={dashboard.pending_driver} />
            <Kpi label="Pending internal" value={dashboard.pending_internal} />
            <Kpi label="Claims linked" value={dashboard.claims_linked} />
            <Kpi label="Orders impacted" value={dashboard.orders_impacted} />
            <Kpi label="Avg first response" value={`${dashboard.avg_first_response_hours}h`} />
            <Kpi label="Avg resolution" value={`${dashboard.avg_resolution_hours}h`} />
            <Kpi
              label="CSAT"
              value={dashboard.customer_satisfaction ? `${dashboard.customer_satisfaction}/5` : "—"}
            />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title="Recent activity">
              <ul className="space-y-2 text-sm">
                {dashboard.recent_activity.map((a) => (
                  <li
                    key={String(a.ticket_id)}
                    className="flex justify-between gap-2 border-b border-primary/5 py-2"
                  >
                    <span className="font-mono text-secondary">{String(a.ticket_number)}</span>
                    <span className="truncate text-muted">{String(a.subject)}</span>
                  </li>
                ))}
              </ul>
            </Panel>
            <Panel title="Team workload">
              <ul className="space-y-2 text-sm">
                {dashboard.team_workload.map((w) => (
                  <li
                    key={String(w.agent_id)}
                    className="flex justify-between border-b border-primary/5 py-2"
                  >
                    <span>{String(w.agent_name)}</span>
                    <span className="text-muted">
                      {String(w.open_tickets)} open · {String(w.urgent_tickets)} urgent
                    </span>
                  </li>
                ))}
              </ul>
            </Panel>
          </div>
        </div>
      )}

      {(tab === "tickets" ||
        tab === "customers" ||
        tab === "merchants" ||
        tab === "drivers" ||
        tab === "internal" ||
        tab === "operations" ||
        tab === "claims" ||
        tab === "finance" ||
        tab === "technical") && (
        <div className="rounded-2xl border border-primary/10 bg-white p-4">
          {(filters.customer_id || filters.merchant_id) && (
            <div className="mb-3 flex flex-wrap items-center gap-2 rounded-xl bg-secondary/5 px-3 py-2 text-sm">
              {filters.customer_id && (
                <span>
                  Customer: <code className="text-xs">{filters.customer_id}</code>
                </span>
              )}
              {filters.merchant_id && (
                <span>
                  Merchant: <code className="text-xs">{filters.merchant_id}</code>
                </span>
              )}
              <Button
                variant="ghost"
                className="text-xs"
                onClick={() =>
                  setFilters((f) => {
                    const next = { ...f };
                    delete next.customer_id;
                    delete next.merchant_id;
                    return next;
                  })
                }
              >
                <X className="h-3.5 w-3.5" /> Clear entity filter
              </Button>
            </div>
          )}
          <div className="mb-4 flex flex-wrap gap-2">
            <input
              type="search"
              placeholder="Ticket #, customer, merchant, tracking, email…"
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
              {TICKET_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s.replace(/_/g, " ")}
                </option>
              ))}
            </select>
            <select
              value={filters.category ?? ""}
              onChange={(e) => setFilters((f) => ({ ...f, category: e.target.value || undefined }))}
              className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
            >
              <option value="">All categories</option>
              {TICKET_CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c.replace(/_/g, " ")}
                </option>
              ))}
            </select>
            <select
              value={filters.priority ?? ""}
              onChange={(e) => setFilters((f) => ({ ...f, priority: e.target.value || undefined }))}
              className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
            >
              <option value="">Priority</option>
              {TICKET_PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
            <select
              value={filters.sla ?? ""}
              onChange={(e) => setFilters((f) => ({ ...f, sla: e.target.value || undefined }))}
              className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
            >
              <option value="">SLA</option>
              <option value="ok">OK</option>
              <option value="at_risk">At risk</option>
              <option value="breached">Breached</option>
              <option value="paused">Paused</option>
            </select>
          </div>

          {selected.length > 0 && (
            <div className="mb-3 flex gap-2 rounded-xl bg-secondary/5 px-3 py-2">
              <span className="text-sm font-medium">{selected.length} selected</span>
              <Button
                variant="outline"
                onClick={async () => {
                  const token = await getApiToken();
                  await supportApi.bulk(token, selected, "auto_assign");
                  setSelected([]);
                  void refetch();
                }}
              >
                Auto-assign
              </Button>
              <Button
                variant="outline"
                onClick={async () => {
                  const token = await getApiToken();
                  await supportApi.bulk(token, selected, "escalate");
                  setSelected([]);
                  void refetch();
                }}
              >
                Escalate
              </Button>
            </div>
          )}

          {isLoading ? (
            <div className="flex justify-center py-12">
              <Spinner />
            </div>
          ) : (
            <SupportGrid rows={rows} selected={selected} onSelect={setSelected} />
          )}
        </div>
      )}

      {tab === "kb" && kb && (
        <Panel title="Knowledge Base">
          <div className="space-y-4">
            {(kb.faq as Array<Record<string, string>> | undefined)?.map((f, i) => (
              <div key={i} className="rounded-xl border border-primary/10 p-3">
                <p className="font-medium">{f.question}</p>
                <p className="mt-1 text-sm text-muted">{f.answer}</p>
              </div>
            ))}
            <h3 className="font-semibold">Articles</h3>
            <ul className="space-y-2">
              {(kb.articles as Array<Record<string, unknown>> | undefined)?.map((a) => (
                <li
                  key={String(a.id)}
                  className="rounded-lg border border-primary/10 px-3 py-2 text-sm"
                >
                  <span className="font-medium">{String(a.title)}</span>
                  <p className="mt-1 text-muted">{String(a.body)}</p>
                </li>
              ))}
            </ul>
          </div>
        </Panel>
      )}

      {tab === "macros" && (
        <Panel title="Saved replies & macros">
          <ul className="space-y-2">
            {macros.map((m) => (
              <li
                key={String(m.id)}
                className="rounded-lg border border-primary/10 px-3 py-2 text-sm"
              >
                <span className="font-medium">{String(m.title)}</span>
                <p className="mt-1 text-muted">{String(m.body)}</p>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      {tab === "automation" && automation && (
        <Panel title="Automation rules">
          <ul className="space-y-2 text-sm">
            {Object.entries(automation).map(([k, v]) => (
              <li key={k} className="flex justify-between border-b border-primary/5 py-2">
                <span className="text-muted">{k.replace(/_/g, " ")}</span>
                <span className="font-medium">{String(v)}</span>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      {tab === "reports" && reports && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Panel title="SLA compliance">
            <p className="text-2xl font-bold text-primary">
              {String(reports.sla_compliance_percent)}%
            </p>
          </Panel>
          <Panel title="Top issues">
            <ul className="space-y-1 text-sm">
              {(reports.top_issues as Array<{ cause: string; count: number }>).map((item) => (
                <li key={item.cause} className="flex justify-between capitalize">
                  <span>{item.cause.replace(/_/g, " ")}</span>
                  <span>{item.count}</span>
                </li>
              ))}
            </ul>
          </Panel>
        </div>
      )}

      {tab === "settings" && slaConfig && (
        <Panel title="SLA configuration">
          <ul className="space-y-2 text-sm">
            {Object.entries(slaConfig).map(([k, v]) => (
              <li key={k} className="flex justify-between border-b border-primary/5 py-2">
                <span className="text-muted">{k.replace(/_/g, " ")}</span>
                <span>{String(v)}</span>
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </div>
  );
}

function Kpi({ label, value, alert }: { label: string; value: string | number; alert?: boolean }) {
  return (
    <div
      className={cn(
        "rounded-xl border border-primary/10 bg-white px-3 py-2 shadow-sm",
        alert && "border-amber-200 bg-amber-50"
      )}
    >
      <p className="text-xs text-muted">{label}</p>
      <p className="text-lg font-bold text-primary">{value}</p>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-primary/10 bg-white p-5">
      <h2 className="mb-4 font-semibold text-primary">{title}</h2>
      {children}
    </div>
  );
}
