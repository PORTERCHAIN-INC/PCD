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
  reportsApi,
  type ClaimsSummary,
  type DeliveryPerformance,
  type DriverRow,
  type ExecutiveReport,
  type ReportsOverview,
  type SavedReport,
  type ScheduledReport,
  type VehicleRow,
} from "@/lib/reports";
import { formatCents } from "@/lib/utils";
import { useCallback, useEffect, useState } from "react";

type Tab =
  | "executive"
  | "delivery"
  | "orders"
  | "invoices"
  | "drivers"
  | "vehicles"
  | "destinations"
  | "claims"
  | "saved"
  | "scheduled";

const TABS: { id: Tab; label: string }[] = [
  { id: "executive", label: "Executive" },
  { id: "delivery", label: "Delivery" },
  { id: "orders", label: "Order volume" },
  { id: "invoices", label: "Invoices" },
  { id: "drivers", label: "Drivers" },
  { id: "vehicles", label: "Vehicles" },
  { id: "destinations", label: "Destinations" },
  { id: "claims", label: "Claims" },
  { id: "saved", label: "Saved" },
  { id: "scheduled", label: "Scheduled" },
];

export default function ReportsClient() {
  const { getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();
  const [tab, setTab] = useState<Tab>("executive");
  const [data, setData] = useState<ReportsOverview | null>(null);
  const [saved, setSaved] = useState<SavedReport[]>([]);
  const [scheduled, setScheduled] = useState<ScheduledReport[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!isSignedIn) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getApiToken();
      const [overview, savedRows, scheduledRows] = await Promise.all([
        reportsApi.overview(token, orgId),
        reportsApi.saved(token, orgId),
        reportsApi.scheduled(token, orgId),
      ]);
      setData(overview);
      setSaved(savedRows);
      setScheduled(scheduledRows);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load reports");
    } finally {
      setLoading(false);
    }
  }, [getApiToken, orgId, isSignedIn]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    void load();
  }, [isLoaded, isSignedIn, load]);

  const handleExport = async (reportType: string, format: "csv" | "xlsx") => {
    setExporting(`${reportType}-${format}`);
    try {
      const token = await getApiToken();
      if (format === "csv") await reportsApi.exportCsv(token, reportType, orgId);
      else await reportsApi.exportExcel(token, reportType, orgId);
    } catch {
      setError("Export failed");
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
    orders: "orders",
    invoices: "invoices",
    drivers: "drivers",
    vehicles: "vehicles",
    destinations: "destinations",
    claims: "claims",
    saved: "orders",
    scheduled: "orders",
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary">Reports</h1>
          <p className="mt-1 text-sm text-muted">
            Executive KPIs, delivery SLA, spend trends, and operational analytics
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

      <nav className="flex flex-wrap gap-2 border-b border-primary/10 pb-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
              tab === t.id ? "bg-primary text-white" : "text-muted hover:bg-primary/5"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "executive" && <ExecutiveTab data={data.executive} />}
      {tab === "delivery" && <DeliveryTab data={data.delivery_performance} />}
      {tab === "orders" && <OrderVolumeTab data={data.order_volume} />}
      {tab === "invoices" && <InvoicesTab data={data.invoice_reports} />}
      {tab === "drivers" && <DriversTab drivers={data.driver_performance.drivers} />}
      {tab === "vehicles" && <VehiclesTab vehicles={data.vehicle_usage.vehicles} />}
      {tab === "destinations" && (
        <DestinationsTab destinations={data.top_destinations.destinations} />
      )}
      {tab === "claims" && <ClaimsTab data={data.claims_summary} />}
      {tab === "saved" && (
        <SavedTab saved={saved} onRefresh={load} getToken={getApiToken} orgId={orgId} />
      )}
      {tab === "scheduled" && (
        <ScheduledTab scheduled={scheduled} onRefresh={load} getToken={getApiToken} orgId={orgId} />
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
              ? formatCents(kpi.value)
              : kpi.format === "percent"
                ? `${kpi.value}%`
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
        <Metric label="Growth (MoM)" value={`${data.growth_percent}%`} />
        <Metric label="Invoice total" value={formatCents(data.invoice_summary_cents)} />
      </div>
      <RankedList
        title="Top routes"
        empty="No route data this month"
        rows={data.top_routes.map((r) => ({ label: r.route, count: r.count }))}
      />
    </div>
  );
}

function DeliveryTab({ data }: { data: DeliveryPerformance }) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Total orders" value={String(data.total_orders)} />
        <Metric label="On-time %" value={`${data.on_time_percent}%`} />
        <Metric label="Delivery SLA %" value={`${data.sla_percent}%`} />
        <Metric label="Success %" value={`${data.delivery_success_percent}%`} />
        <Metric label="Failed deliveries" value={String(data.failed_deliveries)} />
        <Metric label="Failed %" value={`${data.failed_percent}%`} />
        <Metric label="Returned" value={String(data.returned)} />
        <Metric label="Avg delivery (hrs)" value={String(data.avg_delivery_hours)} />
        <Metric label="Avg pickup (hrs)" value={String(data.avg_pickup_hours)} />
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

function DriversTab({ drivers }: { drivers: DriverRow[] }) {
  return (
    <RankedTable
      title="Driver performance"
      empty="No driver assignments this month"
      columns={["Driver", "Orders", "Delivered", "Failed", "Success %"]}
      rows={drivers.map((d) => [
        d.name,
        String(d.orders),
        String(d.delivered),
        String(d.failed),
        `${d.success_percent}%`,
      ])}
    />
  );
}

function VehiclesTab({ vehicles }: { vehicles: VehicleRow[] }) {
  return (
    <RankedTable
      title="Vehicle usage"
      empty="No vehicle usage this month"
      columns={["Vehicle", "Class", "Orders"]}
      rows={vehicles.map((v) => [v.label, v.vehicle_class ?? "—", String(v.orders)])}
    />
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
  onRefresh,
  getToken,
  orgId,
}: {
  saved: SavedReport[];
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
        <h2 className="font-semibold text-primary">Save current view</h2>
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
              <span>
                <span className="font-medium">{r.name}</span>
                <span className="ml-2 text-muted">({r.report_type})</span>
              </span>
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

function ScheduledTab({
  scheduled,
  onRefresh,
  getToken,
  orgId,
}: {
  scheduled: ScheduledReport[];
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [schedule, setSchedule] = useState("weekly");
  const [reportType, setReportType] = useState("executive");

  const handleSchedule = async () => {
    if (!name.trim() || !email.trim()) return;
    const token = await getToken();
    await reportsApi.scheduleReport(
      token,
      { name, report_type: reportType, schedule, email },
      orgId
    );
    setName("");
    await onRefresh();
  };

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Schedule report</h2>
        <p className="mt-1 text-sm text-muted">
          Delivery is queued via the reporting worker when configured.
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <input
            className="rounded-lg border border-primary/20 px-3 py-2 text-sm"
            placeholder="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <input
            className="rounded-lg border border-primary/20 px-3 py-2 text-sm"
            placeholder="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <select
            className="rounded-lg border border-primary/20 px-3 py-2 text-sm"
            value={schedule}
            onChange={(e) => setSchedule(e.target.value)}
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
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
          <Button size="sm" onClick={() => void handleSchedule()}>
            Schedule
          </Button>
        </div>
      </section>
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Scheduled reports</h2>
        <ul className="mt-4 space-y-2 text-sm">
          {scheduled.length === 0 && <li className="text-muted">No scheduled reports</li>}
          {scheduled.map((r) => (
            <li key={r.id} className="flex justify-between gap-4">
              <span>
                <span className="font-medium">{r.name}</span>
                <span className="ml-2 text-muted">
                  {r.schedule} → {r.email} ({r.report_type})
                </span>
              </span>
              <span className={r.active ? "text-green-700" : "text-muted"}>
                {r.active ? "Active" : "Paused"}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-primary/10 bg-white p-5">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-2 text-2xl font-bold text-primary">{value}</p>
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

function RankedTable({
  title,
  empty,
  columns,
  rows,
}: {
  title: string;
  empty: string;
  columns: string[];
  rows: string[][];
}) {
  return (
    <section className="overflow-hidden rounded-2xl border border-primary/10 bg-white">
      <h2 className="border-b border-primary/10 px-6 py-4 font-semibold text-primary">{title}</h2>
      <table className="w-full text-sm">
        <thead className="border-b border-primary/10 bg-primary/5 text-left text-muted">
          <tr>
            {columns.map((c) => (
              <th key={c} className="px-4 py-3 font-medium">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={columns.length} className="px-4 py-6 text-muted">
                {empty}
              </td>
            </tr>
          )}
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-primary/5">
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-3">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
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
