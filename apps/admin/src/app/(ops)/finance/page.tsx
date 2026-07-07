"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, RefreshCw, TrendingUp } from "lucide-react";
import { cn, formatCents } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import FinanceInvoicesGrid from "@/components/finance/FinanceInvoicesGrid";
import FinancePaymentsGrid from "@/components/finance/FinancePaymentsGrid";
import { Button, Spinner } from "@/components/crm/primitives";
import {
  exportGlCsv,
  financeApi,
  INVOICE_STATUSES,
  type FinanceFilters,
  type PayoutRow,
} from "@/lib/finance";

type Tab = "overview" | "invoices" | "payments" | "payouts" | "collections" | "ledger" | "reports";

export default function FinancePage() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const [tab, setTab] = useState<Tab>("overview");
  const [filters, setFilters] = useState<FinanceFilters>({});
  const enabled = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");

  const { data: dashboard } = useQuery({
    queryKey: ["finance-dashboard"],
    enabled,
    queryFn: async () => financeApi.dashboard(await getApiToken()),
  });

  const {
    data: invoices = [],
    isLoading: invLoading,
    refetch,
  } = useQuery({
    queryKey: ["finance-invoices", JSON.stringify(filters)],
    enabled: enabled && (tab === "invoices" || tab === "overview"),
    queryFn: async () => financeApi.invoices(await getApiToken(), filters),
  });

  const { data: payments = [] } = useQuery({
    queryKey: ["finance-payments"],
    enabled: enabled && tab === "payments",
    queryFn: async () => financeApi.payments(await getApiToken()),
  });

  const { data: payouts = [] } = useQuery({
    queryKey: ["finance-payouts"],
    enabled: enabled && tab === "payouts",
    queryFn: async () => financeApi.payouts(await getApiToken()),
  });

  const { data: collections = [] } = useQuery({
    queryKey: ["finance-collections"],
    enabled: enabled && tab === "collections",
    queryFn: async () => financeApi.collections(await getApiToken()),
  });

  const { data: ledger = [] } = useQuery({
    queryKey: ["finance-ledger"],
    enabled: enabled && tab === "ledger",
    queryFn: async () => financeApi.ledger(await getApiToken()),
  });

  const { data: reports } = useQuery({
    queryKey: ["finance-reports"],
    enabled: enabled && tab === "reports",
    queryFn: async () => financeApi.reports(await getApiToken()),
  });

  const TABS: { id: Tab; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "invoices", label: "Invoices" },
    { id: "payments", label: "Payments" },
    { id: "payouts", label: "Driver payouts" },
    { id: "collections", label: "Collections" },
    { id: "ledger", label: "Ledger" },
    { id: "reports", label: "Reports" },
  ];

  async function exportGl() {
    const token = await getApiToken();
    const rows = await financeApi.exportGl(token);
    exportGlCsv(rows);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary">Finance Center</h1>
          <p className="text-sm text-muted">
            Revenue, invoices, payments, payouts, and accounting export
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => void refetch()}>
            <RefreshCw className="h-4 w-4" /> Refresh
          </Button>
          <Button variant="outline" onClick={() => void exportGl()}>
            <Download className="h-4 w-4" /> GL export
          </Button>
        </div>
      </div>

      {dashboard && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
          <Kpi label="Today" value={formatCents(dashboard.today_revenue_cents)} />
          <Kpi label="This month" value={formatCents(dashboard.month_revenue_cents)} />
          <Kpi
            label="Outstanding"
            value={formatCents(dashboard.outstanding_invoices_cents)}
            alert={dashboard.outstanding_invoices_cents > 0}
          />
          <Kpi label="Paid invoices" value={formatCents(dashboard.paid_invoices_cents)} />
          <Kpi label="Pending payments" value={dashboard.pending_payments} />
          <Kpi label="Refunds" value={dashboard.refunds_count} />
          <Kpi label="Credit notes" value={dashboard.credit_notes_count} />
          <Kpi label="Tax collected" value={formatCents(dashboard.taxes_collected_cents)} />
          <Kpi label="Profit est." value={formatCents(dashboard.profit_estimate_cents)} />
          <Kpi label="Cash flow" value={formatCents(dashboard.cash_flow_cents)} />
          <Kpi label="Success rate" value={`${dashboard.payment_success_rate}%`} />
          <Kpi label="Forecast" value={formatCents(dashboard.revenue_forecast_cents)} />
        </div>
      )}

      {dashboard?.revenue_trend?.length ? (
        <div className="rounded-xl border border-primary/10 bg-white p-4">
          <p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase text-muted">
            <TrendingUp className="h-4 w-4" /> Revenue trend (7d)
          </p>
          <div className="flex h-16 items-end gap-1">
            {dashboard.revenue_trend.map((d) => {
              const max = Math.max(...dashboard.revenue_trend.map((x) => x.revenue_cents), 1);
              const h = Math.max(8, (d.revenue_cents / max) * 100);
              return (
                <div key={d.date} className="flex flex-1 flex-col items-center gap-1">
                  <div
                    className="w-full rounded-t bg-secondary/70"
                    style={{ height: `${h}%` }}
                    title={formatCents(d.revenue_cents)}
                  />
                  <span className="text-[10px] text-muted">{d.date.slice(5)}</span>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      {dashboard?.top_merchants?.length ? (
        <div className="rounded-xl border border-primary/10 bg-white px-4 py-3">
          <p className="text-xs font-bold uppercase text-muted">Top merchants (month)</p>
          <ul className="mt-2 space-y-1 text-sm">
            {dashboard.top_merchants.slice(0, 5).map((m) => (
              <li key={m.name} className="flex justify-between">
                <span>{m.name}</span>
                <span className="font-medium">{formatCents(m.revenue_cents)}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <nav className="flex gap-1 overflow-x-auto border-b border-primary/10 pb-px">
        {TABS.map((t) => (
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

      <div className="rounded-2xl border border-primary/10 bg-white p-4">
        {tab === "overview" && (
          <div className="space-y-4">
            <p className="text-sm text-muted">
              Recent invoices — open Invoices tab for full grid and filters.
            </p>
            {invLoading ? <Spinner /> : <FinanceInvoicesGrid rows={invoices.slice(0, 10)} />}
          </div>
        )}

        {tab === "invoices" && (
          <>
            <div className="mb-4 flex flex-wrap gap-2">
              <input
                placeholder="Invoice #, order, tracking…"
                value={filters.search ?? ""}
                onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value || undefined }))}
                className="min-w-[200px] flex-1 rounded-xl border border-primary/10 px-3 py-2 text-sm"
              />
              <select
                value={filters.status ?? ""}
                onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value || undefined }))}
                className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
              >
                <option value="">All statuses</option>
                {INVOICE_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={filters.outstanding_only ?? false}
                  onChange={(e) =>
                    setFilters((f) => ({ ...f, outstanding_only: e.target.checked || undefined }))
                  }
                />
                Outstanding only
              </label>
            </div>
            {invLoading ? (
              <div className="flex justify-center py-12">
                <Spinner />
              </div>
            ) : (
              <FinanceInvoicesGrid rows={invoices} />
            )}
          </>
        )}

        {tab === "payments" && <FinancePaymentsGrid rows={payments} />}

        {tab === "payouts" && <PayoutsTable rows={payouts} />}

        {tab === "collections" && (
          <div className="space-y-2">
            <p className="text-sm text-muted">
              {collections.length} invoice(s) requiring collection
            </p>
            <FinanceInvoicesGrid rows={collections} />
          </div>
        )}

        {tab === "ledger" && (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted">
                <th className="py-2">Kind</th>
                <th>Amount</th>
                <th>Order</th>
                <th>Status</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {ledger.map((e) => (
                <tr key={String(e.id)} className="border-b border-primary/5">
                  <td className="py-2 font-mono text-xs">{String(e.kind)}</td>
                  <td>{e.amount_cents != null ? formatCents(Number(e.amount_cents)) : "—"}</td>
                  <td className="font-mono text-xs">{String(e.order_id || "—")}</td>
                  <td>{String(e.status)}</td>
                  <td>{String(e.created_at).slice(0, 16)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {tab === "reports" && reports && (
          <div className="grid gap-4 md:grid-cols-2 text-sm">
            <div>
              <span className="text-muted">Revenue</span>
              <p className="text-lg font-bold">{formatCents(Number(reports.revenue_cents))}</p>
            </div>
            <div>
              <span className="text-muted">Profit estimate</span>
              <p className="text-lg font-bold">
                {formatCents(Number(reports.profit_estimate_cents))}
              </p>
            </div>
            <div>
              <span className="text-muted">Outstanding</span>
              <p className="text-lg font-bold">{formatCents(Number(reports.outstanding_cents))}</p>
            </div>
            <div>
              <span className="text-muted">Collections</span>
              <p className="text-lg font-bold">{String(reports.collections_count)}</p>
            </div>
            <div>
              <span className="text-muted">Tax summary</span>
              <p className="text-lg font-bold">{formatCents(Number(reports.tax_summary_cents))}</p>
            </div>
            <div>
              <span className="text-muted">Refunds</span>
              <p className="text-lg font-bold">
                {formatCents(Number(reports.refund_analysis_cents))}
              </p>
            </div>
          </div>
        )}
      </div>
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

function PayoutsTable({ rows }: { rows: PayoutRow[] }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b text-left text-muted">
          <th className="py-2">Driver</th>
          <th>Amount</th>
          <th>Status</th>
          <th>Reference</th>
          <th>Date</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((p) => (
          <tr key={p.payout_id} className="border-b border-primary/5">
            <td className="py-2">{p.driver_name || p.driver_id}</td>
            <td>{formatCents(p.amount_cents)}</td>
            <td className="capitalize">{p.status}</td>
            <td className="font-mono text-xs">{p.reference || "—"}</td>
            <td>{String(p.created_at).slice(0, 10)}</td>
          </tr>
        ))}
        {!rows.length && (
          <tr>
            <td colSpan={5} className="py-8 text-center text-muted">
              No payouts
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}
