"use client";

import { Suspense, useCallback, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Banknote, Download, RefreshCw, TrendingUp, Wallet } from "lucide-react";
import { cn, formatCents } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import FinanceCollectionsPanel from "@/components/finance/FinanceCollectionsPanel";
import FinanceInvoicesGrid from "@/components/finance/FinanceInvoicesGrid";
import FinancePaymentsGrid from "@/components/finance/FinancePaymentsGrid";
import FinanceMerchantArPanel from "@/components/finance/FinanceMerchantArPanel";
import { ListPager } from "@/components/crm/ListPager";
import { Button, EmptyState, Spinner } from "@/components/crm/primitives";
import { SettingsPageHeader } from "@/components/settings/ui/SettingsPrimitives";
import {
  exportGlCsv,
  financeApi,
  INVOICE_STATUSES,
  type FinanceFilters,
  type PayoutRow,
} from "@/lib/finance";
import { withStaffStepUp } from "@/lib/staff-step-up";

type Tab =
  | "overview"
  | "invoices"
  | "payments"
  | "payouts"
  | "collections"
  | "merchant-ar"
  | "ledger"
  | "reports";

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "invoices", label: "Invoices" },
  { id: "payments", label: "Payments" },
  { id: "payouts", label: "Payouts" },
  { id: "collections", label: "Collections" },
  { id: "merchant-ar", label: "Merchant AR" },
  { id: "ledger", label: "Ledger" },
  { id: "reports", label: "Reports" },
];

const TAB_IDS = new Set<Tab>(TABS.map((t) => t.id));

function FinancePageInner() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const queryClient = useQueryClient();
  const enabled = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");

  const tabParam = searchParams.get("tab");
  const tab: Tab = tabParam && TAB_IDS.has(tabParam as Tab) ? (tabParam as Tab) : "overview";

  const [filters, setFilters] = useState<FinanceFilters>({});
  const [invOffset, setInvOffset] = useState(0);
  const [payOffset, setPayOffset] = useState(0);
  const [remindingId, setRemindingId] = useState<string | null>(null);

  const setTab = useCallback(
    (next: Tab) => {
      const params = new URLSearchParams(searchParams.toString());
      if (next === "overview") params.delete("tab");
      else params.set("tab", next);
      const q = params.toString();
      router.replace(q ? `${pathname}?${q}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams]
  );

  const {
    data: dashboard,
    isLoading: dashLoading,
    isFetching: dashFetching,
    refetch: refetchDash,
  } = useQuery({
    queryKey: ["finance-dashboard"],
    enabled,
    queryFn: async () => financeApi.dashboard(await getApiToken()),
  });

  const {
    data: invoicePage,
    isLoading: invLoading,
    refetch: refetchInv,
  } = useQuery({
    queryKey: ["finance-invoices", JSON.stringify(filters), tab, invOffset],
    enabled: enabled && (tab === "invoices" || tab === "overview"),
    queryFn: async () =>
      financeApi.invoices(
        await getApiToken(),
        tab === "overview"
          ? { ...filters, limit: 8, offset: 0 }
          : { ...filters, limit: 50, offset: invOffset }
      ),
  });
  const invoices = invoicePage?.items ?? [];

  const { data: paymentPage, isLoading: payLoading } = useQuery({
    queryKey: ["finance-payments", payOffset],
    enabled: enabled && tab === "payments",
    queryFn: async () =>
      financeApi.payments(await getApiToken(), undefined, { limit: 50, offset: payOffset }),
  });
  const payments = paymentPage?.items ?? [];

  const { data: payouts = [], isLoading: payoutLoading } = useQuery({
    queryKey: ["finance-payouts"],
    enabled: enabled && tab === "payouts",
    queryFn: async () => financeApi.payouts(await getApiToken()),
  });

  const { data: collections = [], isLoading: colLoading } = useQuery({
    queryKey: ["finance-collections"],
    enabled: enabled && tab === "collections",
    queryFn: async () => financeApi.collections(await getApiToken()),
  });

  const overdueCollections = useMemo(
    () => collections.filter((r) => r.days_overdue > 0),
    [collections]
  );

  const { data: ledger = [], isLoading: ledgerLoading } = useQuery({
    queryKey: ["finance-ledger"],
    enabled: enabled && tab === "ledger",
    queryFn: async () => financeApi.ledger(await getApiToken()),
  });

  const { data: reports, isLoading: reportsLoading } = useQuery({
    queryKey: ["finance-reports"],
    enabled: enabled && tab === "reports",
    queryFn: async () => financeApi.reports(await getApiToken()),
  });

  async function remindInvoice(invoiceId: string) {
    setRemindingId(invoiceId);
    try {
      const token = await getApiToken();
      await withStaffStepUp(token, () => financeApi.remindInvoice(token, invoiceId));
      await queryClient.invalidateQueries({ queryKey: ["finance-collections"] });
      await queryClient.invalidateQueries({ queryKey: ["finance-invoices"] });
    } finally {
      setRemindingId(null);
    }
  }

  async function exportGl() {
    const token = await getApiToken();
    const rows = await financeApi.exportGl(token);
    exportGlCsv(rows);
  }

  async function refreshAll() {
    await refetchDash();
    if (tab === "invoices" || tab === "overview") await refetchInv();
  }

  const primaryKpis = useMemo(() => {
    if (!dashboard) return [];
    return [
      {
        label: "Today",
        value: formatCents(dashboard.today_revenue_cents),
        icon: Banknote,
      },
      {
        label: "This month",
        value: formatCents(dashboard.month_revenue_cents),
        icon: TrendingUp,
      },
      {
        label: "Outstanding",
        value: formatCents(dashboard.outstanding_invoices_cents),
        icon: AlertTriangle,
        alert: dashboard.outstanding_invoices_cents > 0,
        hint:
          dashboard.outstanding_invoice_count > 0
            ? `${dashboard.outstanding_invoice_count} open`
            : undefined,
      },
      {
        label: "Cash flow",
        value: formatCents(dashboard.cash_flow_cents),
        icon: Wallet,
      },
    ];
  }, [dashboard]);

  const secondaryKpis = useMemo(() => {
    if (!dashboard) return [];
    return [
      { label: "Paid", value: formatCents(dashboard.paid_invoices_cents) },
      { label: "Pending payments", value: String(dashboard.pending_payments) },
      { label: "Success rate", value: `${dashboard.payment_success_rate}%` },
      { label: "Tax collected", value: formatCents(dashboard.taxes_collected_cents) },
      { label: "Refunds", value: String(dashboard.refunds_count) },
      { label: "Profit est.", value: formatCents(dashboard.profit_estimate_cents) },
      { label: "Forecast", value: formatCents(dashboard.revenue_forecast_cents) },
      { label: "Overdue", value: String(dashboard.overdue_invoices_count) },
    ];
  }, [dashboard]);

  return (
    <div className="space-y-6">
      <SettingsPageHeader
        title="Finance"
        description="Revenue, invoices, payments, payouts, and accounting export"
        actions={
          <>
            <Button variant="outline" disabled={dashFetching} onClick={() => void refreshAll()}>
              <RefreshCw className={cn("h-4 w-4", dashFetching && "animate-spin")} />
              Refresh
            </Button>
            <Button variant="outline" onClick={() => void exportGl()}>
              <Download className="h-4 w-4" />
              GL export
            </Button>
          </>
        }
      />

      {dashLoading && !dashboard ? (
        <div className="flex justify-center py-12">
          <Spinner label="Loading finance…" />
        </div>
      ) : null}

      {dashboard ? (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {primaryKpis.map((k) => (
            <div
              key={k.label}
              className={cn(
                "rounded-2xl border bg-white px-4 py-3.5 shadow-sm",
                k.alert ? "border-amber-200 bg-amber-50/80" : "border-primary/10"
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-xs font-medium uppercase tracking-wide text-muted">{k.label}</p>
                <k.icon className={cn("h-4 w-4", k.alert ? "text-amber-600" : "text-secondary")} />
              </div>
              <p className="mt-1.5 text-2xl font-bold tabular-nums text-primary">{k.value}</p>
              {k.hint ? <p className="mt-0.5 text-xs text-amber-700">{k.hint}</p> : null}
            </div>
          ))}
        </div>
      ) : null}

      <div className="flex flex-wrap gap-1.5 rounded-2xl border border-primary/10 bg-white p-1.5 shadow-sm">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={cn(
              "rounded-xl px-3.5 py-2 text-sm font-medium transition",
              tab === t.id
                ? "bg-secondary text-white shadow-sm"
                : "text-muted hover:bg-gray-bg hover:text-primary"
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="min-h-[20rem]">
        {tab === "overview" && dashboard ? (
          <div className="space-y-4">
            <div className="grid gap-4 lg:grid-cols-3">
              <div className="rounded-2xl border border-primary/10 bg-white p-4 shadow-sm lg:col-span-2">
                <p className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted">
                  <TrendingUp className="h-3.5 w-3.5 text-secondary" />
                  Revenue trend (7d)
                </p>
                {dashboard.revenue_trend?.length ? (
                  <div className="flex h-36 items-end gap-1.5">
                    {dashboard.revenue_trend.map((d) => {
                      const max = Math.max(
                        ...dashboard.revenue_trend.map((x) => x.revenue_cents),
                        1
                      );
                      const h = Math.max(12, Math.round((d.revenue_cents / max) * 100));
                      return (
                        <div
                          key={d.date}
                          className="flex min-w-0 flex-1 flex-col items-center gap-1.5"
                        >
                          <div
                            className="w-full max-w-[2.5rem] rounded-t-md bg-gradient-to-t from-secondary to-sky-400/80"
                            style={{ height: `${h}%` }}
                            title={`${d.date}: ${formatCents(d.revenue_cents)}`}
                          />
                          <span className="text-[10px] tabular-nums text-muted">
                            {d.date.slice(5)}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <EmptyState
                    title="No trend data yet"
                    hint="Revenue will appear after paid invoices."
                  />
                )}
              </div>

              <div className="rounded-2xl border border-primary/10 bg-white p-4 shadow-sm">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">
                  Top merchants (month)
                </p>
                {dashboard.top_merchants?.length ? (
                  <ul className="space-y-2.5">
                    {dashboard.top_merchants.slice(0, 6).map((m, i) => (
                      <li
                        key={`${m.name}-${i}`}
                        className="flex items-center justify-between gap-3 text-sm"
                      >
                        <span className="truncate font-medium text-primary">{m.name}</span>
                        <span className="shrink-0 tabular-nums text-muted">
                          {formatCents(m.revenue_cents)}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <EmptyState title="No merchant revenue yet" />
                )}
              </div>
            </div>

            <div className="rounded-2xl border border-primary/10 bg-white p-4 shadow-sm">
              <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">
                More metrics
              </p>
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                {secondaryKpis.map((k) => (
                  <div
                    key={k.label}
                    className="rounded-xl border border-primary/5 bg-gray-bg/40 px-3 py-2"
                  >
                    <p className="text-[11px] text-muted">{k.label}</p>
                    <p className="text-sm font-semibold tabular-nums text-primary">{k.value}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-primary/10 bg-white p-4 shadow-sm">
              <div className="mb-3 flex items-center justify-between gap-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                  Recent invoices
                </p>
                <button
                  type="button"
                  onClick={() => setTab("invoices")}
                  className="text-xs font-semibold text-secondary hover:underline"
                >
                  View all →
                </button>
              </div>
              {invLoading ? (
                <Spinner />
              ) : (
                <FinanceInvoicesGrid rows={invoices.slice(0, 8)} dense hideToolbar />
              )}
            </div>
          </div>
        ) : null}

        {tab === "invoices" ? (
          <Panel>
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <input
                placeholder="Search invoice #, order, tracking…"
                value={filters.search ?? ""}
                onChange={(e) => {
                  setInvOffset(0);
                  setFilters((f) => ({ ...f, search: e.target.value || undefined }));
                }}
                className="min-w-[220px] flex-1 rounded-xl border border-primary/10 bg-white px-3 py-2 text-sm"
              />
              <select
                value={filters.status ?? ""}
                onChange={(e) => {
                  setInvOffset(0);
                  setFilters((f) => ({ ...f, status: e.target.value || undefined }));
                }}
                className="rounded-xl border border-primary/10 bg-white px-3 py-2 text-sm"
              >
                <option value="">All statuses</option>
                {INVOICE_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
              <label className="flex items-center gap-2 rounded-xl border border-primary/10 bg-white px-3 py-2 text-sm text-muted">
                <input
                  type="checkbox"
                  checked={filters.outstanding_only ?? false}
                  onChange={(e) => {
                    setInvOffset(0);
                    setFilters((f) => ({
                      ...f,
                      outstanding_only: e.target.checked || undefined,
                    }));
                  }}
                />
                Outstanding only
              </label>
            </div>
            {invLoading ? (
              <div className="flex justify-center py-12">
                <Spinner />
              </div>
            ) : (
              <>
                <FinanceInvoicesGrid rows={invoices} hideToolbar={false} />
                <ListPager
                  total={invoicePage?.total ?? 0}
                  limit={invoicePage?.limit ?? 50}
                  offset={invOffset}
                  onPage={setInvOffset}
                />
              </>
            )}
          </Panel>
        ) : null}

        {tab === "payments" ? (
          <Panel>
            {payLoading ? (
              <div className="flex justify-center py-12">
                <Spinner />
              </div>
            ) : (
              <>
                <FinancePaymentsGrid rows={payments} />
                <ListPager
                  total={paymentPage?.total ?? 0}
                  limit={paymentPage?.limit ?? 50}
                  offset={payOffset}
                  onPage={setPayOffset}
                />
              </>
            )}
          </Panel>
        ) : null}

        {tab === "payouts" ? (
          <Panel>
            {payoutLoading ? (
              <div className="flex justify-center py-12">
                <Spinner />
              </div>
            ) : (
              <PayoutsTable rows={payouts} />
            )}
          </Panel>
        ) : null}

        {tab === "collections" ? (
          <Panel>
            <p className="mb-3 text-sm text-muted">
              {collections.length} invoice{collections.length === 1 ? "" : "s"} needing collection
              {collections.length > 0
                ? ` · ${formatCents(collections.reduce((sum, r) => sum + (r.outstanding_cents || 0), 0))} invoiced and unpaid`
                : ""}
              {overdueCollections.length > 0
                ? ` · ${overdueCollections.length} past due (${formatCents(
                    overdueCollections.reduce((sum, r) => sum + (r.outstanding_cents || 0), 0)
                  )})`
                : ""}
            </p>
            {colLoading ? (
              <div className="flex justify-center py-12">
                <Spinner />
              </div>
            ) : collections.length === 0 ? (
              <EmptyState
                title="No collections due"
                hint="Outstanding and overdue invoices appear here."
              />
            ) : (
              <FinanceCollectionsPanel
                rows={collections}
                onRemind={(id) => void remindInvoice(id)}
                remindingId={remindingId}
              />
            )}
          </Panel>
        ) : null}

        {tab === "merchant-ar" ? (
          <Panel>
            <FinanceMerchantArPanel />
          </Panel>
        ) : null}

        {tab === "ledger" ? (
          <Panel>
            {ledgerLoading ? (
              <div className="flex justify-center py-12">
                <Spinner />
              </div>
            ) : ledger.length === 0 ? (
              <EmptyState title="Ledger is empty" hint="Posted finance events show up here." />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[36rem] text-left text-sm">
                  <thead>
                    <tr className="border-b border-primary/10 text-xs uppercase tracking-wide text-muted">
                      <th className="px-2 py-2.5 font-medium">Kind</th>
                      <th className="px-2 py-2.5 font-medium">Amount</th>
                      <th className="px-2 py-2.5 font-medium">Order</th>
                      <th className="px-2 py-2.5 font-medium">Status</th>
                      <th className="px-2 py-2.5 font-medium">Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ledger.map((e) => (
                      <tr
                        key={String(e.id)}
                        className="border-b border-primary/5 hover:bg-gray-bg/50"
                      >
                        <td className="px-2 py-2.5 font-mono text-xs">{String(e.kind)}</td>
                        <td className="px-2 py-2.5 tabular-nums">
                          {e.amount_cents != null ? formatCents(Number(e.amount_cents)) : "—"}
                        </td>
                        <td className="px-2 py-2.5 font-mono text-xs">
                          {String(e.order_id || "—")}
                        </td>
                        <td className="px-2 py-2.5 capitalize">{String(e.status)}</td>
                        <td className="px-2 py-2.5 text-muted">
                          {String(e.created_at).slice(0, 16).replace("T", " ")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        ) : null}

        {tab === "reports" ? (
          <Panel>
            {reportsLoading || !reports ? (
              <div className="flex justify-center py-12">
                <Spinner />
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {[
                  { label: "Revenue", value: formatCents(Number(reports.revenue_cents)) },
                  {
                    label: "Profit estimate",
                    value: formatCents(Number(reports.profit_estimate_cents)),
                  },
                  {
                    label: "Outstanding",
                    value: formatCents(Number(reports.outstanding_cents)),
                  },
                  { label: "Collections", value: String(reports.collections_count) },
                  {
                    label: "Tax summary",
                    value: formatCents(Number(reports.tax_summary_cents)),
                  },
                  {
                    label: "Refunds",
                    value: formatCents(Number(reports.refund_analysis_cents)),
                  },
                ].map((r) => (
                  <div
                    key={r.label}
                    className="rounded-xl border border-primary/8 bg-gray-bg/30 px-4 py-3"
                  >
                    <p className="text-xs text-muted">{r.label}</p>
                    <p className="mt-1 text-lg font-bold tabular-nums text-primary">{r.value}</p>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        ) : null}
      </div>
    </div>
  );
}

function Panel({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-primary/10 bg-white p-4 shadow-sm sm:p-5">
      {children}
    </div>
  );
}

function PayoutsTable({ rows }: { rows: PayoutRow[] }) {
  if (!rows.length) {
    return <EmptyState title="No driver payouts" hint="Settled and pending payouts appear here." />;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[36rem] text-left text-sm">
        <thead>
          <tr className="border-b border-primary/10 text-xs uppercase tracking-wide text-muted">
            <th className="px-2 py-2.5 font-medium">Driver</th>
            <th className="px-2 py-2.5 font-medium">Amount</th>
            <th className="px-2 py-2.5 font-medium">Status</th>
            <th className="px-2 py-2.5 font-medium">Reference</th>
            <th className="px-2 py-2.5 font-medium">Date</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <tr key={p.payout_id} className="border-b border-primary/5 hover:bg-gray-bg/50">
              <td className="px-2 py-2.5 font-medium">{p.driver_name || p.driver_id}</td>
              <td className="px-2 py-2.5 tabular-nums">{formatCents(p.amount_cents)}</td>
              <td className="px-2 py-2.5 capitalize">{p.status}</td>
              <td className="px-2 py-2.5 font-mono text-xs">{p.reference || "—"}</td>
              <td className="px-2 py-2.5 text-muted">{String(p.created_at).slice(0, 10)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function FinancePage() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center py-16">
          <Spinner label="Loading finance…" />
        </div>
      }
    >
      <FinancePageInner />
    </Suspense>
  );
}
