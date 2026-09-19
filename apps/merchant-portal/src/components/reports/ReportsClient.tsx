"use client";

import Button from "@/components/ui/Button";
import { EmptyState } from "@porterchain/ui/empty-state";
import { PageSkeleton } from "@porterchain/ui/loading";
import {
  OrdersPerformanceChart,
  PerformanceChart,
  SpendPerformanceChart,
} from "@/components/dashboard/PerformanceChart";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import {
  REPORT_TYPES,
  formatPercent,
  reportsApi,
  type ClaimsSummary,
  type DeliveryPerformance,
  type ExecutiveReport,
  type ReportsOverview,
  type SavedReport,
} from "@/lib/reports";
import { formatCents } from "@/lib/utils";
import { useCallback, useEffect, useState } from "react";

type Tab = "executive" | "delivery" | "invoices" | "claims" | "saved";

const TABS: { id: Tab; label: string }[] = [
  { id: "executive", label: "Overview" },
  { id: "delivery", label: "Delivery" },
  { id: "invoices", label: "Invoices" },
  { id: "claims", label: "Claims" },
  { id: "saved", label: "Saved" },
];

const TAB_ALIASES: Record<string, Tab> = {
  executive: "executive",
  delivery: "delivery",
  orders: "delivery",
  destinations: "delivery",
  drivers: "delivery",
  vehicles: "delivery",
  invoices: "invoices",
  claims: "claims",
  saved: "saved",
};

function parseReportTab(value: string | null | undefined): Tab {
  if (value && value in TAB_ALIASES) return TAB_ALIASES[value];
  return "executive";
}

export default function ReportsClient() {
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
  const [tab, setTab] = useState<Tab>("executive");
  const [data, setData] = useState<ReportsOverview | null>(null);
  const [saved, setSaved] = useState<SavedReport[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!isSignedIn || !orgId) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getApiToken();
      const [overview, savedRows] = await Promise.all([
        reportsApi.overview(token, orgId),
        reportsApi.saved(token, orgId),
      ]);
      setData(overview);
      setSaved(savedRows);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load reports");
    } finally {
      setLoading(false);
    }
  }, [getApiToken, orgId, isSignedIn]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn || !orgId) return;
    void load();
  }, [isLoaded, isSignedIn, orgId, load]);

  const handleExport = async (reportType: string, format: "csv" | "xlsx") => {
    setExporting(`${reportType}-${format}`);
    try {
      const token = await getApiToken();
      if (format === "csv") await reportsApi.exportCsv(token, reportType, orgId);
      else await reportsApi.exportExcel(token, reportType, orgId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not download that report.");
    } finally {
      setExporting(null);
    }
  };

  if (!isLoaded || (loading && !data)) {
    return <PageSkeleton rows={4} />;
  }

  if (error && !data) {
    return (
      <EmptyState
        title="Reports unavailable"
        hint={error}
        action={<Button onClick={() => void load()}>Retry</Button>}
      />
    );
  }

  if (!data) return null;

  const exportTypeForTab: Record<Tab, string> = {
    executive: "delivery",
    delivery: "delivery",
    invoices: "invoices",
    claims: "claims",
    saved: "orders",
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary">Reports</h1>
          <p className="mt-1 text-sm text-muted">
            {data.period?.label ?? "This calendar month"}
            {data.period?.timezone ? ` · ${data.period.timezone}` : ""}. On-time is promised time vs
            delivered time (30-minute grace). A dash means there is not enough completed work to
            score.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={!!exporting}
            onClick={() => void handleExport(exportTypeForTab[tab], "csv")}
          >
            Export CSV
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={!!exporting}
            onClick={() => void handleExport(exportTypeForTab[tab], "xlsx")}
          >
            Export Excel
          </Button>
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <nav
        className="ops-tab-rail rounded-2xl border border-primary/10 bg-white"
        aria-label="Reports"
      >
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`min-h-10 shrink-0 rounded-xl px-3 py-1.5 text-sm font-medium whitespace-nowrap transition ${
              tab === t.id ? "bg-primary text-white" : "text-muted hover:bg-primary/5"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "executive" && <ExecutiveTab data={data.executive} />}
      {tab === "delivery" && (
        <div className="space-y-6">
          <DeliveryTab data={data.delivery_performance} />
          <OrderVolumeTab data={data.order_volume} />
          <DestinationsTab destinations={data.top_destinations.destinations} />
        </div>
      )}
      {tab === "invoices" && <InvoicesTab data={data.invoice_reports} />}
      {tab === "claims" && <ClaimsTab data={data.claims_summary} />}
      {tab === "saved" && (
        <SavedTab
          saved={saved}
          onOpen={(reportType) => setTab(parseReportTab(reportType))}
          onRefresh={load}
          getToken={getApiToken}
          orgId={orgId}
        />
      )}
    </div>
  );
}

function KpiGrid({ kpis }: { kpis: ExecutiveReport["kpis"] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      {kpis.map((kpi) => (
        <div key={kpi.label} className="rounded-2xl border border-primary/10 bg-white p-5">
          <p className="text-sm text-muted">{kpi.label}</p>
          <p className="mt-2 text-2xl font-bold text-primary">
            {kpi.format === "currency"
              ? kpi.value == null
                ? "—"
                : formatCents(kpi.value)
              : kpi.format === "percent"
                ? formatPercent(kpi.value)
                : kpi.value == null
                  ? "—"
                  : kpi.value}
          </p>
        </div>
      ))}
    </div>
  );
}

function ExecutiveTab({ data }: { data: ExecutiveReport }) {
  const monthlyOrders = data.charts.monthly_trends.labels.map((label, i) => ({
    label,
    value: data.charts.monthly_trends.orders[i] ?? 0,
  }));
  const monthlySpend = data.charts.monthly_trends.labels.map((label, i) => ({
    label,
    value: data.charts.monthly_trends.spend_cents[i] ?? 0,
  }));

  return (
    <div className="space-y-6">
      <KpiGrid kpis={data.kpis} />
      <div className="grid gap-4 lg:grid-cols-2">
        <OrdersPerformanceChart series={data.charts.daily_orders} />
        <SpendPerformanceChart series={data.charts.daily_spend_cents} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <PerformanceChart
          title="Monthly order volume"
          subtitle="Last 6 months"
          series={monthlyOrders}
        />
        <PerformanceChart
          title="Monthly spend"
          subtitle="Last 6 months — operational spend"
          series={monthlySpend}
          formatValue={(v) => formatCents(v)}
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="In progress" value={String(data.orders_in_progress)} />
        <Metric label="Delivered today" value={String(data.delivered_today)} />
        <Metric label="Growth (MoM)" value={formatPercent(data.growth_percent)} />
        <Metric label="Invoice total" value={formatCents(data.invoice_summary_cents)} />
      </div>
      <RankedList
        title="Top routes"
        empty="No route data this month"
        rows={data.top_routes.map((r) => ({ label: r.route, count: r.count }))}
      />
      <SpendAttribution
        byChannel={data.spend_by_channel}
        byModel={data.spend_by_pricing_model}
        topBands={data.top_pricing_bands}
      />
    </div>
  );
}

function DeliveryTab({ data }: { data: DeliveryPerformance }) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Bookings this month" value={String(data.total_orders)} />
        <Metric label="Delivered" value={String(data.delivered)} />
        <Metric
          label="On-time"
          value={formatPercent(data.on_time_percent)}
          hint={
            data.on_time_sample_size
              ? `${data.on_time_orders ?? 0} of ${data.on_time_sample_size} scored`
              : "Needs a promised time and a delivered event"
          }
        />
        <Metric
          label="Delivered of bookings"
          value={formatPercent(data.delivery_success_percent)}
        />
        <Metric label="Failed deliveries" value={String(data.failed_deliveries)} />
        <Metric label="Failed of bookings" value={formatPercent(data.failed_percent)} />
        <Metric label="Returned" value={String(data.returned)} />
        <Metric
          label="Avg delivery (hrs)"
          value={data.avg_delivery_hours == null ? "—" : String(data.avg_delivery_hours)}
        />
        <Metric
          label="Avg pickup (hrs)"
          value={data.avg_pickup_hours == null ? "—" : String(data.avg_pickup_hours)}
        />
      </div>
    </div>
  );
}

function OrderVolumeTab({ data }: { data: ReportsOverview["order_volume"] }) {
  const monthlyOrders = data.monthly_trends.labels.map((label, i) => ({
    label,
    value: data.monthly_trends.orders[i] ?? 0,
  }));

  return (
    <div className="space-y-6">
      <div className="grid gap-4 lg:grid-cols-2">
        <OrdersPerformanceChart series={data.daily_orders} />
        <PerformanceChart title="Monthly orders" subtitle="6-month trend" series={monthlyOrders} />
      </div>
      <RankedList
        title="Top routes by volume"
        empty="No orders this period"
        rows={data.top_routes.map((r) => ({ label: r.route, count: r.count }))}
      />
    </div>
  );
}

function InvoicesTab({ data }: { data: ReportsOverview["invoice_reports"] }) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <Metric label="Invoices" value={String(data.invoice_count)} />
        <Metric label="Total" value={formatCents(data.invoice_total_cents)} />
        <Metric label="Tax" value={formatCents(data.tax_cents)} />
      </div>
      <SpendAttribution
        byChannel={data.spend_by_channel}
        byModel={data.spend_by_pricing_model}
        topBands={data.top_pricing_bands}
      />
      <section className="overflow-hidden rounded-2xl border border-primary/10 bg-white">
        <table className="w-full text-sm">
          <thead className="border-b border-primary/10 bg-primary/5 text-left text-muted">
            <tr>
              <th className="px-4 py-3 font-medium">Invoice</th>
              <th className="px-4 py-3 font-medium">Order</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium text-right">Amount</th>
            </tr>
          </thead>
          <tbody>
            {data.invoices.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-muted">
                  No invoices this period
                </td>
              </tr>
            )}
            {data.invoices.map((inv) => (
              <tr key={String(inv.invoice_id)} className="border-b border-primary/5">
                <td className="px-4 py-3">{String(inv.invoice_number ?? "—")}</td>
                <td className="px-4 py-3 text-muted">{String(inv.order_number ?? "—")}</td>
                <td className="px-4 py-3">{String(inv.status ?? "—")}</td>
                <td className="px-4 py-3 text-right font-medium">
                  {formatCents(Number(inv.amount_cents ?? 0))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function SpendAttribution({
  byChannel,
  byModel,
  topBands,
}: {
  byChannel?: Array<{ channel: string; orders: number; spend_cents: number }>;
  byModel?: Array<{ pricing_model: string; orders: number; spend_cents: number }>;
  topBands?: Array<{ band: string; pricing_model: string; orders: number; spend_cents: number }>;
}) {
  if (!byChannel?.length && !byModel?.length && !topBands?.length) return null;
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <SpendTable
        title="Spend by channel"
        empty="No channel spend this period"
        rows={(byChannel ?? []).map((r) => ({
          label: r.channel,
          orders: r.orders,
          spend_cents: r.spend_cents,
        }))}
      />
      <SpendTable
        title="Spend by pricing model"
        empty="No pricing-model spend"
        rows={(byModel ?? []).map((r) => ({
          label: r.pricing_model.toUpperCase(),
          orders: r.orders,
          spend_cents: r.spend_cents,
        }))}
      />
      <SpendTable
        title="Top bands"
        empty="No band data yet"
        rows={(topBands ?? []).map((r) => ({
          label: r.band,
          orders: r.orders,
          spend_cents: r.spend_cents,
        }))}
      />
    </div>
  );
}

function SpendTable({
  title,
  empty,
  rows,
}: {
  title: string;
  empty: string;
  rows: Array<{ label: string; orders: number; spend_cents: number }>;
}) {
  return (
    <section className="overflow-hidden rounded-2xl border border-primary/10 bg-white">
      <div className="border-b border-primary/10 px-4 py-3">
        <h2 className="font-semibold text-primary">{title}</h2>
      </div>
      {rows.length === 0 ? (
        <p className="px-4 py-6 text-sm text-muted">{empty}</p>
      ) : (
        <table className="w-full text-sm">
          <thead className="border-b border-primary/5 text-left text-muted">
            <tr>
              <th className="px-4 py-2 font-medium">Slice</th>
              <th className="px-4 py-2 font-medium">Orders</th>
              <th className="px-4 py-2 font-medium text-right">Spend</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label} className="border-b border-primary/5">
                <td className="px-4 py-2 capitalize">{row.label}</td>
                <td className="px-4 py-2">{row.orders}</td>
                <td className="px-4 py-2 text-right font-medium">{formatCents(row.spend_cents)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function DestinationsTab({
  destinations,
}: {
  destinations: Array<{ destination: string; count: number }>;
}) {
  return (
    <RankedList
      title="Top destinations"
      empty="No destination data"
      rows={destinations.map((d) => ({ label: d.destination, count: d.count }))}
    />
  );
}

function ClaimsTab({ data }: { data: ClaimsSummary }) {
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

function SavedTab({
  saved,
  onOpen,
  onRefresh,
  getToken,
  orgId,
}: {
  saved: SavedReport[];
  onOpen: (reportType: string) => void;
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [name, setName] = useState("");
  const [reportType, setReportType] = useState("orders");

  const handleSave = async () => {
    if (!name.trim()) return;
    const token = await getToken();
    await reportsApi.saveReport(token, { name, report_type: reportType }, orgId);
    setName("");
    await onRefresh();
  };

  const handleDelete = async (id: string) => {
    const token = await getToken();
    await reportsApi.deleteSaved(token, id, orgId);
    await onRefresh();
  };

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Save a report shortcut</h2>
        <p className="mt-1 text-sm text-muted">Opens that report. It does not email anyone.</p>
        <div className="mt-4 flex flex-wrap gap-3">
          <input
            className="rounded-lg border border-primary/20 px-3 py-2 text-sm"
            placeholder="Report name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <select
            className="rounded-lg border border-primary/20 px-3 py-2 text-sm"
            value={reportType}
            onChange={(e) => setReportType(e.target.value)}
          >
            {REPORT_TYPES.map((t) => (
              <option key={t.id} value={t.id}>
                {t.label}
              </option>
            ))}
          </select>
          <Button size="sm" onClick={() => void handleSave()}>
            Save report
          </Button>
        </div>
      </section>
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Saved reports</h2>
        <ul className="mt-4 space-y-2 text-sm">
          {saved.length === 0 && <li className="text-muted">No saved reports</li>}
          {saved.map((r) => (
            <li key={r.id} className="flex items-center justify-between gap-4">
              <button
                type="button"
                className="text-left text-secondary hover:underline"
                onClick={() => onOpen(r.report_type)}
              >
                <span className="font-medium">{r.name}</span>
                <span className="ml-2 text-muted">({r.report_type})</span>
              </button>
              <Button variant="outline" size="sm" onClick={() => void handleDelete(r.id)}>
                Remove
              </Button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function Metric({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-2xl border border-primary/10 bg-white p-5">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-2 text-2xl font-bold text-primary">{value}</p>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}

function RankedList({
  title,
  empty,
  rows,
}: {
  title: string;
  empty: string;
  rows: Array<{ label: string; count: number }>;
}) {
  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">{title}</h2>
      <ul className="mt-4 space-y-2 text-sm">
        {rows.length === 0 && <li className="text-muted">{empty}</li>}
        {rows.map((r) => (
          <li key={r.label} className="flex justify-between gap-4">
            <span className="truncate text-muted">{r.label}</span>
            <span className="font-medium">{r.count}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function KeyValueList({
  title,
  items,
  empty,
}: {
  title: string;
  items: [string, number][];
  empty: string;
}) {
  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">{title}</h2>
      <ul className="mt-4 space-y-2 text-sm">
        {items.length === 0 && <li className="text-muted">{empty}</li>}
        {items.map(([k, v]) => (
          <li key={k} className="flex justify-between gap-4">
            <span className="text-muted">{k}</span>
            <span className="font-medium">{v}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
