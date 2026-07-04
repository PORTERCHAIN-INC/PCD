"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  BarChart3,
  Bookmark,
  Calendar,
  Download,
  LineChart,
  RefreshCw,
  Sparkles,
  Wrench,
} from "lucide-react";
import { cn, formatCents } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import ReportChart, { barChartOption, lineChartOption, pieChartOption } from "@/components/reports/ReportChart";
import { Button, Spinner } from "@/components/crm/primitives";
import {
  dictToPairs,
  exportReportCsv,
  reportsApi,
  type ReportCategory,
} from "@/lib/reports";

type Tab =
  | "dashboard"
  | "categories"
  | "saved"
  | "scheduled"
  | "builder"
  | "exports"
  | "forecast"
  | "modules";

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: "dashboard", label: "KPI Dashboard", icon: <BarChart3 className="h-4 w-4" /> },
  { id: "categories", label: "Report Categories", icon: <LineChart className="h-4 w-4" /> },
  { id: "saved", label: "Saved Reports", icon: <Bookmark className="h-4 w-4" /> },
  { id: "scheduled", label: "Scheduled", icon: <Calendar className="h-4 w-4" /> },
  { id: "builder", label: "Report Builder", icon: <Wrench className="h-4 w-4" /> },
  { id: "exports", label: "Exports", icon: <Download className="h-4 w-4" /> },
  { id: "forecast", label: "Forecast", icon: <Sparkles className="h-4 w-4" /> },
  { id: "modules", label: "Module Data", icon: <BarChart3 className="h-4 w-4" /> },
];

export default function ReportsPage() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const enabled = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");
  const [tab, setTab] = useState<Tab>("dashboard");
  const [activeCategory, setActiveCategory] = useState<string | null>(null);

  const { data: center, isLoading, refetch } = useQuery({
    queryKey: ["reports-center"],
    enabled,
    queryFn: async () => reportsApi.center(await getApiToken()),
  });

  const { data: categoryData } = useQuery({
    queryKey: ["reports-category", activeCategory],
    enabled: enabled && Boolean(activeCategory),
    queryFn: async () => reportsApi.category(await getApiToken(), activeCategory!),
  });

  const { data: saved = [] } = useQuery({
    queryKey: ["reports-saved"],
    enabled: enabled && (tab === "saved" || tab === "dashboard"),
    queryFn: async () => reportsApi.saved(await getApiToken()),
  });

  const { data: scheduled = [] } = useQuery({
    queryKey: ["reports-scheduled"],
    enabled: enabled && tab === "scheduled",
    queryFn: async () => reportsApi.scheduled(await getApiToken()),
  });

  const { data: datasets = [] } = useQuery({
    queryKey: ["reports-datasets"],
    enabled: enabled && tab === "builder",
    queryFn: async () => reportsApi.builderDatasets(await getApiToken()),
  });

  const [builderDataset, setBuilderDataset] = useState("orders");
  const [builderGroupBy, setBuilderGroupBy] = useState("state");
  const { data: builderPreview, refetch: previewBuilder } = useQuery({
    queryKey: ["reports-builder", builderDataset, builderGroupBy],
    enabled: false,
    queryFn: async () =>
      reportsApi.builderPreview(await getApiToken(), {
        dataset: builderDataset,
        group_by: builderGroupBy,
        metric: "count",
      }),
  });

  const revenueTrendOption = useMemo(() => {
    if (!center?.trends) return barChartOption([], []);
    return lineChartOption(center.trends.labels, [
      { name: "Orders", data: center.trends.orders },
      {
        name: "Revenue",
        data: center.trends.revenue_cents.map((c) => Math.round(c / 100)),
      },
    ]);
  }, [center]);

  const topMerchantsOption = useMemo(() => {
    const pairs = (center?.executive?.top_merchants as Array<[string, number]> | undefined) ?? [];
    return barChartOption(
      pairs.map((p) => p[0]),
      pairs.map((p) => p[1]),
      "Top merchants"
    );
  }, [center]);

  if (isLoading && !center) {
    return (
      <div className="flex justify-center py-20">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary">Reports & Business Intelligence</h1>
          <p className="text-sm text-muted">
            Enterprise analytics — consumes data from all Porterchain modules
          </p>
        </div>
        <Button variant="outline" onClick={() => void refetch()}>
          <RefreshCw className="h-4 w-4" /> Refresh
        </Button>
      </div>

      {center?.smart?.ai_summary ? (
        <div className="rounded-2xl border border-secondary/20 bg-secondary/5 px-4 py-3 text-sm">
          <p className="flex items-center gap-2 font-semibold text-secondary">
            <Sparkles className="h-4 w-4" /> AI summary
          </p>
          <p className="mt-1 text-primary">{String(center.smart.ai_summary)}</p>
        </div>
      ) : null}

      <nav className="flex gap-1 overflow-x-auto border-b border-primary/10 pb-px">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={cn(
              "inline-flex shrink-0 items-center gap-1.5 rounded-t-lg px-3 py-2 text-sm font-medium",
              tab === t.id ? "border border-b-0 border-primary/10 bg-white text-secondary" : "text-muted"
            )}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "dashboard" && center && (
        <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
            <Kpi label="Revenue" value={formatCents(Number(center.executive.revenue_cents))} />
            <Kpi label="Profit (est.)" value={formatCents(Number(center.executive.profit_estimate_cents))} />
            <Kpi label="Growth" value={`${center.executive.growth_percent}%`} />
            <Kpi label="Orders" value={String(center.summary.monthly_orders)} />
            <Kpi label="AOV" value={formatCents(Number(center.executive.average_order_value_cents))} />
            <Kpi label="Delivery SLA" value={`${center.summary.delivery_sla_percent}%`} />
            <Kpi label="CSAT" value={String(center.executive.customer_satisfaction || "—")} />
            <Kpi label="Merchants" value={String(center.summary.active_merchants)} />
            <Kpi label="Drivers" value={String(center.summary.active_drivers)} />
            <Kpi label="Cancellation" value={`${center.summary.cancellation_rate_percent}%`} />
            <Kpi label="Claim rate" value={`${center.summary.claim_rate_percent}%`} />
            <Kpi
              label="Forecast"
              value={formatCents(Number(center.executive.forecast_revenue_cents))}
            />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title="Revenue & orders trend">
              <ReportChart option={revenueTrendOption} />
            </Panel>
            <Panel title="Top merchants">
              <ReportChart option={topMerchantsOption} />
            </Panel>
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            <RoleDashboard title="Operations" data={center.operations} />
            <RoleDashboard title="Delivery performance" data={center.delivery_performance} />
            <PinnedReports reports={saved.filter((r) => r.pinned)} />
          </div>
        </motion.div>
      )}

      {tab === "categories" && center && (
        <div className="space-y-6">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {center.categories.map((c: ReportCategory) => (
              <button
                key={c.id}
                type="button"
                onClick={() => setActiveCategory(c.id)}
                className={cn(
                  "rounded-xl border p-4 text-left transition-colors",
                  activeCategory === c.id
                    ? "border-secondary bg-secondary/5"
                    : "border-primary/10 bg-white hover:border-secondary/40"
                )}
              >
                <p className="font-semibold text-primary">{c.label}</p>
                <p className="mt-1 text-xs text-muted capitalize">{c.module} module</p>
              </button>
            ))}
          </div>
          {activeCategory && categoryData && (
            <CategoryPanel categoryId={activeCategory} data={categoryData} />
          )}
        </div>
      )}

      {tab === "saved" && (
        <Panel title="Saved reports">
          <div className="mb-3">
            <Button
              variant="primary"
              onClick={() => {
                void (async () => {
                  const name = prompt("Report name");
                  const cat = prompt("Category id (e.g. executive, orders, finance)");
                  if (!name || !cat) return;
                  await reportsApi.saveReport(await getApiToken(), {
                    name,
                    category_id: cat,
                    pinned: false,
                  });
                  void refetch();
                })();
              }}
            >
              Save current view
            </Button>
          </div>
          <ul className="space-y-2">
            {saved.map((r) => (
              <li key={r.id} className="flex items-center justify-between rounded-lg border border-primary/10 px-3 py-2 text-sm">
                <span>
                  <span className="font-medium">{r.name}</span>
                  <span className="ml-2 text-xs text-muted">{r.category_id}</span>
                </span>
                <Button
                  variant="outline"
                  onClick={() => {
                    setActiveCategory(r.category_id);
                    setTab("categories");
                  }}
                >
                  Open
                </Button>
              </li>
            ))}
            {!saved.length && <p className="text-sm text-muted">No saved reports yet</p>}
          </ul>
        </Panel>
      )}

      {tab === "scheduled" && (
        <Panel title="Scheduled reports">
          <Button
            variant="primary"
            className="mb-4"
            onClick={() => {
              void (async () => {
                const name = prompt("Schedule name");
                const cat = prompt("Category id");
                const schedule = prompt("Schedule (daily, weekly, monthly)");
                const email = prompt("Email delivery address");
                if (!name || !cat || !schedule || !email) return;
                await reportsApi.scheduleReport(await getApiToken(), {
                  name,
                  category_id: cat,
                  schedule,
                  email,
                });
              })();
            }}
          >
            New schedule
          </Button>
          <ul className="space-y-2 text-sm">
            {scheduled.map((s) => (
              <li key={s.id} className="rounded-lg border border-primary/10 px-3 py-2">
                <span className="font-medium">{s.name}</span>
                <span className="ml-2 text-muted capitalize">
                  {s.schedule} → {s.email}
                </span>
              </li>
            ))}
            {!scheduled.length && <p className="text-muted">No scheduled reports</p>}
          </ul>
        </Panel>
      )}

      {tab === "builder" && (
        <Panel title="Report builder">
          <div className="mb-4 flex flex-wrap gap-2">
            <select
              value={builderDataset}
              onChange={(e) => setBuilderDataset(e.target.value)}
              className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
            >
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.label}
                </option>
              ))}
            </select>
            <select
              value={builderGroupBy}
              onChange={(e) => setBuilderGroupBy(e.target.value)}
              className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
            >
              {(datasets.find((d) => d.id === builderDataset)?.group_by ?? ["state"]).map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
            <Button variant="primary" onClick={() => void previewBuilder()}>
              Preview
            </Button>
          </div>
          {builderPreview?.series?.length ? (
            <ReportChart
              option={barChartOption(
                builderPreview.series.map((s) => s.label),
                builderPreview.series.map((s) => s.value)
              )}
            />
          ) : (
            <p className="text-sm text-muted">Choose dataset and fields, then preview</p>
          )}
        </Panel>
      )}

      {tab === "exports" && center && (
        <Panel title="Exports">
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              onClick={() => {
                void (async () => {
                  const token = await getApiToken();
                  await reportsApi.exportAudit(token, "executive", "csv");
                  exportReportCsv(
                    "executive-summary.csv",
                    ["metric", "value"],
                    [
                      ["revenue", String(center.executive.revenue_cents)],
                      ["orders", String(center.summary.monthly_orders)],
                      ["sla", String(center.summary.delivery_sla_percent)],
                    ]
                  );
                })();
              }}
            >
              <Download className="h-4 w-4" /> CSV executive
            </Button>
            <Button variant="outline" onClick={() => window.print()}>
              Print dashboard
            </Button>
          </div>
          <p className="mt-3 text-xs text-muted">
            PDF and email delivery use scheduled reports. GL export available in Finance Center.
          </p>
        </Panel>
      )}

      {tab === "forecast" && center && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Panel title="Revenue forecast">
            <p className="mb-4 text-3xl font-bold text-primary">
              {formatCents(Number(center.executive.forecast_revenue_cents))}
            </p>
            <p className="text-sm text-muted">Next-month projection based on recent trend (+5%)</p>
            <ReportChart option={revenueTrendOption} height={280} />
          </Panel>
          <Panel title="Trend analysis">
            <Row label="Direction" value={String(center.smart.trend_direction)} />
            {(center.smart.anomalies as string[] | undefined)?.map((a) => (
              <p key={a} className="mt-2 text-sm text-amber-700">
                {a}
              </p>
            ))}
          </Panel>
        </div>
      )}

      {tab === "modules" && center && (
        <div className="grid gap-4 lg:grid-cols-2">
          <ModuleChart
            title="Claims by type"
            data={dictToPairs(
              (center.modules.claims as Record<string, unknown>)?.by_type as Record<string, number>
            )}
          />
          <ModuleChart
            title="Support by type"
            data={dictToPairs(
              (center.modules.support as Record<string, unknown>)?.by_type as Record<string, number>
            )}
          />
          <ModuleChart
            title="Finance top merchants"
            data={((center.modules.finance as Record<string, unknown>)?.top_merchants as Array<[string, number]>) ?? []}
          />
        </div>
      )}
    </div>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-primary/10 bg-white px-3 py-2 shadow-sm">
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

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-primary/5 py-2 text-sm">
      <span className="text-muted">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

function RoleDashboard({ title, data }: { title: string; data: Record<string, unknown> }) {
  return (
    <Panel title={title}>
      {Object.entries(data)
        .slice(0, 8)
        .map(([k, v]) => (
          <Row key={k} label={k.replace(/_/g, " ")} value={String(v)} />
        ))}
    </Panel>
  );
}

function PinnedReports({ reports }: { reports: Array<{ id: string; name: string; category_id: string }> }) {
  return (
    <Panel title="Pinned reports">
      {reports.map((r) => (
        <Row key={r.id} label={r.name} value={r.category_id} />
      ))}
      {!reports.length && <p className="text-sm text-muted">Pin saved reports for quick access</p>}
    </Panel>
  );
}

function ModuleChart({
  title,
  data,
}: {
  title: string;
  data: Array<[string, number]>;
}) {
  if (!data.length) return <Panel title={title}><p className="text-sm text-muted">No data</p></Panel>;
  return (
    <Panel title={title}>
      <ReportChart option={pieChartOption(data.map((d) => d[0]), data.map((d) => d[1]))} height={280} />
    </Panel>
  );
}

function CategoryPanel({ categoryId, data }: { categoryId: string; data: Record<string, unknown> }) {
  const pairs = useMemo(() => {
    for (const key of ["top_merchants", "top_drivers", "by_type", "by_merchant", "by_driver"]) {
      const val = data[key];
      if (Array.isArray(val) && val.length && Array.isArray(val[0])) {
        return val as Array<[string, number]>;
      }
      if (val && typeof val === "object" && !Array.isArray(val)) {
        return dictToPairs(val as Record<string, number>);
      }
    }
    return [] as Array<[string, number]>;
  }, [data]);

  return (
    <Panel title={categoryId.replace(/_/g, " ")}>
      {pairs.length > 0 ? (
        <ReportChart
          option={barChartOption(
            pairs.map((p) => p[0]),
            pairs.map((p) => p[1])
          )}
        />
      ) : (
        <pre className="max-h-96 overflow-auto rounded-xl bg-gray-bg p-3 text-xs">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </Panel>
  );
}
