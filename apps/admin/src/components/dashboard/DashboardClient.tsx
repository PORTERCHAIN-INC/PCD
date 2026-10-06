"use client";

import { useEffect, useMemo, useState } from "react";
import { PageSkeleton } from "@porterchain/ui/loading";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  Bell,
  Building2,
  Calendar,
  CheckCircle2,
  Clock,
  LayoutGrid,
  Maximize2,
  Package,
  RefreshCw,
  Search,
  Settings2,
  TrendingUp,
  Truck,
  Wallet,
  Zap,
} from "lucide-react";
import { cn, formatCents } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { Button } from "@/components/crm/primitives";
import ReportChart, { lineChartOption, sparklineOption } from "@/components/reports/ReportChart";
import { ops } from "@/lib/operations";
import {
  dashboardApi,
  DASHBOARD_WIDGETS,
  healthStatus,
  loadWidgetLayout,
  saveWidgetLayout,
  type DashboardCenter,
  type WidgetId,
} from "@/lib/dashboard";
import { INTEGRATION_HEALTH_CORE_KEYS, INTEGRATION_HEALTH_LABELS } from "@/lib/health";
import { relativeTime } from "@/lib/crmFormat";
import AdminPage from "@/components/layout/AdminPage";
import DashboardGraphics from "@/components/dashboard/DashboardGraphics";
import { NumberTicker } from "@/components/dashboard/magic";

const fadeUp = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0 },
};

export default function DashboardClient() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const enabled = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");
  const [now, setNow] = useState<Date | null>(null);
  const [search, setSearch] = useState("");
  const [layoutOpen, setLayoutOpen] = useState(false);
  const [widgets, setWidgets] = useState<Record<WidgetId, boolean>>(
    () =>
      Object.fromEntries(
        DASHBOARD_WIDGETS.map((widget) => [widget.id, widget.defaultVisible])
      ) as Record<WidgetId, boolean>
  );

  useEffect(() => {
    setWidgets(loadWidgetLayout());
    setNow(new Date());
    const t = setInterval(() => setNow(new Date()), 30_000);
    return () => clearInterval(t);
  }, []);

  const {
    data: center,
    isLoading,
    isError,
    error,
    refetch,
    dataUpdatedAt,
  } = useQuery({
    queryKey: ["dashboard-center"],
    enabled,
    queryFn: async () => dashboardApi.center(await getApiToken()),
    retry: 1,
  });

  const { data: liveOps } = useQuery({
    queryKey: ["dashboard-ops-stats"],
    enabled: enabled && widgets.operations,
    queryFn: async () => ops.stats(await getApiToken()),
  });

  const { data: searchHits = [] } = useQuery({
    queryKey: ["dashboard-search", search],
    enabled: enabled && search.length >= 2,
    queryFn: async () => dashboardApi.search(await getApiToken(), search),
  });

  const operations = { ...(center?.operations ?? {}), ...(liveOps ?? {}) };

  const chartOption = useMemo(() => {
    if (!center?.trends) return null;
    return lineChartOption(
      center.trends.labels,
      [
        { name: "Revenue", data: center.trends.revenue_cents.map((c) => Math.round(c / 100)) },
        { name: "Orders", data: center.trends.orders },
      ],
      { markAnomalies: true }
    );
  }, [center?.trends]);

  function toggleWidget(id: WidgetId) {
    const next = { ...widgets, [id]: !widgets[id] };
    setWidgets(next);
    saveWidgetLayout(next);
  }

  function toggleFullscreen() {
    if (!document.fullscreenElement) void document.documentElement.requestFullscreen();
    else void document.exitFullscreen();
  }

  if (!center && (!enabled || isLoading)) {
    return (
      <div className="flex justify-center py-24">
        <PageSkeleton rows={3} />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-6 text-sm">
        <p className="font-semibold text-red-800">Failed to load command center</p>
        <p className="mt-1 text-red-700">
          {error instanceof Error ? error.message : "Unknown error"}
        </p>
        <Button variant="outline" className="mt-4" onClick={() => void refetch()}>
          <RefreshCw className="h-4 w-4" /> Retry
        </Button>
      </div>
    );
  }

  if (!center) return null;

  return (
    <AdminPage>
      <motion.div initial={false} animate="show" variants={fadeUp}>
        <CommandHeader
          center={center}
          now={now}
          search={search}
          searchHits={searchHits}
          onSearch={setSearch}
          onRefresh={() => void refetch()}
          onFullscreen={toggleFullscreen}
          onLayout={() => setLayoutOpen((o) => !o)}
          updatedAt={dataUpdatedAt}
        />
      </motion.div>

      {layoutOpen && (
        <WidgetLayoutPanel
          widgets={widgets}
          onToggle={toggleWidget}
          onClose={() => setLayoutOpen(false)}
        />
      )}

      {widgets.kpis && <KpiGrid center={center} />}

      {/* Graphics canvas covers ops / orders / CRM summaries — skip duplicate panels. */}
      {widgets.smart && (
        <div className="mt-5">
          <DashboardGraphics center={center} operations={operations} />
        </div>
      )}

      <div className="mt-5 grid gap-5 xl:grid-cols-[1fr_320px]">
        <div className="space-y-5">
          {widgets.operations && !widgets.smart && (
            <Panel title="Operations center" icon={<Zap className="h-4 w-4" />}>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <MiniKpi label="Dispatch queue" value={Number(operations.waiting_dispatch ?? 0)} />
                <MiniKpi label="Assigned" value={Number(center.orders.assigned ?? 0)} />
                <MiniKpi label="Pickup queue" value={Number(operations.pending_pickups ?? 0)} />
                <MiniKpi
                  label="Delivery queue"
                  value={Number(operations.pending_deliveries ?? 0)}
                />
                <MiniKpi label="Delayed" value={Number(operations.delayed_orders ?? 0)} alert />
                <MiniKpi
                  label="Emergency"
                  value={Number(operations.high_priority_orders ?? 0)}
                  alert
                />
                <MiniKpi label="SLA breached" value={Number(operations.sla_breached ?? 0)} alert />
                <MiniKpi label="Exceptions" value={Number(operations.open_exceptions ?? 0)} />
              </div>
              <Link
                href="/operations"
                className="mt-3 inline-block text-sm text-secondary hover:underline"
              >
                Open control tower →
              </Link>
            </Panel>
          )}

          <div className="grid gap-5 lg:grid-cols-2">
            {widgets.orders && !widgets.smart && <OrdersPanel center={center} />}
            {widgets.booking && <BookingPanel center={center} />}
            {widgets.finance && <FinancePanel center={center} />}
            {widgets.support && <SupportPanel center={center} />}
            {widgets.claims && <ClaimsPanel center={center} />}
            {widgets.crm && !widgets.smart && <CrmPanel center={center} />}
            {widgets.merchants && <MerchantsPanel center={center} />}
            {widgets.drivers && <DriversPanel center={center} />}
            {widgets.fleet && <FleetPanel center={center} />}
          </div>

          {widgets.reports && !widgets.smart && chartOption && (
            <Panel title="Revenue & order trends" icon={<TrendingUp className="h-4 w-4" />}>
              <ReportChart option={chartOption} height={280} />
            </Panel>
          )}

          {widgets.activity && (
            <Panel title="Activity timeline" icon={<Activity className="h-4 w-4" />}>
              <ul className="max-h-64 space-y-2 overflow-y-auto text-sm">
                {center.activity.map((e, i) => (
                  <li
                    key={`${e.id}-${e.occurred_at ?? i}`}
                    className="flex justify-between border-b border-primary/5 py-1.5"
                  >
                    <span>
                      <span className="font-mono text-xs text-secondary">{e.event_type}</span>{" "}
                      {e.aggregate_type} · {(e.aggregate_id ?? "").toString().slice(0, 8)}
                    </span>
                    <span className="text-xs text-muted">
                      {e.occurred_at ? relativeTime(e.occurred_at) : ""}
                    </span>
                  </li>
                ))}
                {!center.activity.length && <p className="text-muted">No recent domain events</p>}
              </ul>
            </Panel>
          )}

          {widgets.health && <SystemHealthPanel health={center.system_health} />}
        </div>

        {widgets.sidebar && (
          <aside className="space-y-4">
            <RightSidebar center={center} />
          </aside>
        )}
      </div>
    </AdminPage>
  );
}

function CommandHeader({
  center,
  now,
  search,
  searchHits,
  onSearch,
  onRefresh,
  onFullscreen,
  onLayout,
  updatedAt,
}: {
  center: DashboardCenter;
  now: Date | null;
  search: string;
  searchHits: Array<{ type: string; id: string; label: string; subtitle?: string; href?: string }>;
  onSearch: (v: string) => void;
  onRefresh: () => void;
  onFullscreen: () => void;
  onLayout: () => void;
  updatedAt: number;
}) {
  return (
    <div className={cn("rounded-2xl border border-primary/10 p-4", "bg-white")}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-primary">
            <LayoutGrid className="h-7 w-7 text-secondary" />
            Executive Command Center
          </h1>
          <p className="mt-1 flex flex-wrap items-center gap-3 text-sm text-muted">
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" />
              {now
                ? now.toLocaleDateString(undefined, {
                    weekday: "long",
                    month: "long",
                    day: "numeric",
                  })
                : ""}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              {now ? now.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }) : ""}
            </span>
            <span>{center.meta.company}</span>
            <span className="rounded-full bg-secondary/10 px-2 py-0.5 text-xs font-medium uppercase text-secondary">
              {center.meta.environment}
            </span>
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={onRefresh}>
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button variant="outline" onClick={onFullscreen}>
            <Maximize2 className="h-4 w-4" />
          </Button>
          <Button variant="outline" onClick={onLayout}>
            <Settings2 className="h-4 w-4" /> Layout
          </Button>
        </div>
      </div>

      <div className="relative mt-4">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        <input
          type="search"
          value={search}
          onChange={(e) => onSearch(e.target.value)}
          placeholder="Search orders, merchants, drivers, claims, support…"
          className="w-full rounded-xl border border-primary/10 py-2 pl-10 pr-3 text-sm"
        />
        {searchHits.length > 0 && (
          <ul className="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-xl border border-primary/10 bg-white shadow-lg">
            {searchHits.map((h) => (
              <li key={`${h.type}-${h.id}`}>
                <Link
                  href={h.href ?? "/dashboard"}
                  className="block px-3 py-2 text-sm hover:bg-secondary/5"
                  onClick={() => onSearch("")}
                >
                  <span className="font-medium">{h.label}</span>
                  <span className="ml-2 text-xs text-muted">{h.type}</span>
                  {h.subtitle && <span className="ml-2 text-xs text-muted">{h.subtitle}</span>}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {center.quick_actions.map((a) => (
          <Link
            key={a.id}
            href={a.href}
            className="rounded-lg border border-primary/10 px-3 py-1.5 text-xs font-medium hover:bg-secondary/5"
          >
            {a.label}
          </Link>
        ))}
      </div>
      <p className="mt-2 text-xs text-muted">
        Updated {relativeTime(new Date(updatedAt).toISOString())} · v{center.meta.version}
      </p>
    </div>
  );
}

function KpiGrid({ center }: { center: DashboardCenter }) {
  const k = center.kpis;
  const revSpark = center.trends.revenue_cents.map((c) => Math.round(c / 100));
  const orderSpark = center.trends.orders;
  const cards: Array<{
    label: string;
    value: string;
    alert?: boolean;
    spark?: number[];
    sparkColor?: string;
    numeric?: number;
    prefix?: string;
    suffix?: string;
    decimals?: number;
  }> = [
    {
      label: "Today's revenue",
      value: formatCents(Number(k.revenue_today_cents ?? k.todays_revenue_cents ?? 0)),
      numeric: Math.round(Number(k.revenue_today_cents ?? k.todays_revenue_cents ?? 0) / 100),
      prefix: "$",
      spark: revSpark.length > 1 ? revSpark : undefined,
      sparkColor: "#2563eb",
    },
    {
      label: "Orders today",
      value: String(k.orders_today ?? k.todays_bookings ?? 0),
      numeric: Number(k.orders_today ?? k.todays_bookings ?? 0),
      spark: orderSpark.length > 1 ? orderSpark : undefined,
      sparkColor: "#0ea5e9",
    },
    {
      label: "In progress",
      value: String(k.orders_in_progress ?? 0),
      numeric: Number(k.orders_in_progress ?? 0),
    },
    {
      label: "Vehicles active",
      value: String(k.vehicles_active ?? 0),
      numeric: Number(k.vehicles_active ?? 0),
    },
    {
      label: "Awaiting dispatch",
      value: String(k.orders_waiting_dispatch ?? 0),
      numeric: Number(k.orders_waiting_dispatch ?? 0),
    },
    {
      label: "Late deliveries",
      value: String(k.late_deliveries ?? 0),
      numeric: Number(k.late_deliveries ?? 0),
      alert: true,
    },
    {
      label: "Open claims",
      value: String(k.open_claims ?? 0),
      numeric: Number(k.open_claims ?? 0),
    },
    {
      label: "Support tickets",
      value: String(k.open_support_tickets ?? 0),
      numeric: Number(k.open_support_tickets ?? 0),
    },
    {
      label: "Merchants",
      value: String(k.merchant_growth ?? 0),
      numeric: Number(k.merchant_growth ?? 0),
    },
    {
      label: "New customers",
      value: String(k.customer_growth ?? 0),
      numeric: Number(k.customer_growth ?? 0),
    },
    { label: "Avg delivery (h)", value: String(k.avg_delivery_hours ?? "—") },
    {
      label: "Profit estimate",
      value: formatCents(Number(k.profit_estimate_cents ?? 0)),
      numeric: Math.round(Number(k.profit_estimate_cents ?? 0) / 100),
      prefix: "$",
    },
  ];
  return (
    <motion.div
      className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-6"
      initial={false}
      animate="show"
      variants={{
        hidden: {},
        show: { transition: { staggerChildren: 0.03 } },
      }}
    >
      {cards.map((c) => (
        <motion.div
          key={c.label}
          variants={fadeUp}
          className={cn(
            "rounded-xl border px-3 py-2.5",
            "border-primary/10 bg-white",
            c.alert && Number(c.value) > 0 && "border-amber-200 bg-amber-50"
          )}
        >
          <p className="text-xs text-muted">{c.label}</p>
          <p className="text-lg font-bold text-primary">
            {c.numeric != null ? (
              <NumberTicker
                value={c.numeric}
                prefix={c.prefix}
                suffix={c.suffix}
                decimalPlaces={c.decimals ?? 0}
              />
            ) : (
              c.value
            )}
          </p>
          {c.spark && (
            <div className="-mx-1 mt-1 h-8 overflow-hidden">
              <ReportChart option={sparklineOption(c.spark, c.sparkColor)} height={32} compact />
            </div>
          )}
        </motion.div>
      ))}
    </motion.div>
  );
}

function Panel({
  title,
  icon,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-4">
      <h2 className="mb-3 flex items-center gap-2 font-semibold text-primary">
        {icon}
        {title}
      </h2>
      {children}
    </section>
  );
}

function MiniKpi({ label, value, alert }: { label: string; value: number; alert?: boolean }) {
  return (
    <div
      className={cn(
        "rounded-lg border border-primary/5 px-2 py-1.5",
        alert && value > 0 && "border-amber-200 bg-amber-50"
      )}
    >
      <p className="text-xs text-muted">{label}</p>
      <p className="font-semibold">{value}</p>
    </div>
  );
}

function OrdersPanel({ center }: { center: DashboardCenter }) {
  const o = center.orders;
  return (
    <Panel title="Orders" icon={<Package className="h-4 w-4" />}>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <Row label="Waiting dispatch" value={Number(o.waiting_dispatch ?? 0)} />
        <Row label="Assigned" value={Number(o.assigned ?? 0)} />
        <Row label="Picked up" value={Number(o.picked_up ?? 0)} />
        <Row label="In transit" value={Number(o.orders_in_progress ?? 0)} />
        <Row label="Delivered" value={Number(o.delivered ?? 0)} />
        <Row label="Failed" value={Number(o.failed ?? 0)} />
        <Row label="Returned" value={Number(o.returned ?? 0)} />
        <Row label="Claims" value={Number(o.claims ?? 0)} />
      </div>
      <Link href="/orders" className="mt-2 inline-block text-sm text-secondary hover:underline">
        Order center →
      </Link>
    </Panel>
  );
}

function BookingPanel({ center }: { center: DashboardCenter }) {
  const b = center.booking;
  return (
    <Panel title="Booking" icon={<Wallet className="h-4 w-4" />}>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <Row label="Total drafts" value={Number(b.total_drafts ?? 0)} />
        <Row label="Confirmed" value={Number(b.confirmed_drafts ?? 0)} />
        <Row label="Active" value={Number(b.active_drafts ?? 0)} />
        <Row label="Abandoned" value={Number(b.abandoned_now ?? 0)} />
        <Row label="Conversion %" value={Number(b.conversion_rate_percent ?? 0)} />
        <Row label="Pending quotes" value={center.kpis.pending_quotes as number} />
      </div>
      <Link
        href="/booking-drafts"
        className="mt-2 inline-block text-sm text-secondary hover:underline"
      >
        Booking drafts →
      </Link>
    </Panel>
  );
}

function FinancePanel({ center }: { center: DashboardCenter }) {
  const f = center.finance;
  return (
    <Panel title="Finance" icon={<Wallet className="h-4 w-4" />}>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <Row label="Today" value={formatCents(Number(f.today_revenue_cents ?? 0))} />
        <Row label="Outstanding" value={formatCents(Number(f.outstanding_invoices_cents ?? 0))} />
        <Row label="Pending payments" value={Number(f.pending_payments ?? 0)} />
        <Row label="Refunds" value={Number(f.refunds_count ?? 0)} />
        <Row
          label="Driver payouts"
          value={formatCents(Number(f.driver_payouts_pending_cents ?? 0))}
        />
        <Row label="Cash flow" value={formatCents(Number(f.cash_flow_cents ?? 0))} />
      </div>
      <Link href="/finance" className="mt-2 inline-block text-sm text-secondary hover:underline">
        Finance center →
      </Link>
    </Panel>
  );
}

function SupportPanel({ center }: { center: DashboardCenter }) {
  const s = center.support;
  return (
    <Panel title="Support" icon={<Bell className="h-4 w-4" />}>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <Row label="Open" value={Number(s.open_tickets ?? 0)} />
        <Row label="Urgent" value={Number(s.urgent_tickets ?? 0)} />
        <Row label="SLA breaches" value={Number(s.sla_breaches ?? 0)} />
        <Row label="Avg response (h)" value={Number(s.avg_first_response_hours ?? 0)} />
      </div>
      <Link href="/support" className="mt-2 inline-block text-sm text-secondary hover:underline">
        Support center →
      </Link>
    </Panel>
  );
}

function ClaimsPanel({ center }: { center: DashboardCenter }) {
  const c = center.claims;
  return (
    <Panel title="Claims" icon={<AlertTriangle className="h-4 w-4" />}>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <Row label="Open" value={Number(c.open_claims ?? 0)} />
        <Row label="Investigating" value={Number(c.under_investigation ?? 0)} />
        <Row label="Insurance" value={Number(c.insurance_claims ?? 0)} />
        <Row label="Compensation" value={formatCents(Number(c.total_compensation_cents ?? 0))} />
      </div>
      <Link href="/claims" className="mt-2 inline-block text-sm text-secondary hover:underline">
        Claims center →
      </Link>
    </Panel>
  );
}

function CrmPanel({ center }: { center: DashboardCenter }) {
  const c = center.crm;
  return (
    <Panel title="CRM" icon={<Building2 className="h-4 w-4" />}>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <Row label="New leads" value={Number(c.new_leads ?? 0)} />
        <Row label="Follow-ups today" value={Number(c.todays_follow_ups ?? 0)} />
        <Row label="Meetings today" value={Number(c.meetings_today ?? 0)} />
        <Row label="Open deals" value={Number(c.open_deals ?? 0)} />
        <Row label="Won this month" value={Number(c.won_deals_this_month ?? 0)} />
        <Row label="Overdue tasks" value={Number(c.overdue_tasks ?? 0)} />
        <Row label="Pipeline" value={formatCents(Number(c.pipeline_value_cents ?? 0))} />
        <Row label="Contracts pending" value={Number(c.contracts_pending ?? 0)} />
      </div>
      <Link href="/leads" className="mt-2 inline-block text-sm text-secondary hover:underline">
        Leads →
      </Link>
    </Panel>
  );
}

function MerchantsPanel({ center }: { center: DashboardCenter }) {
  const m = center.merchants as Record<string, unknown>;
  const topRev =
    (m.top_by_revenue as Array<{ id?: string; name?: string; revenue_cents?: number }>) ?? [];
  const topOrders =
    (m.top_by_orders as Array<{ id?: string; name?: string; orders?: number }>) ?? [];
  return (
    <Panel title="Merchants" icon={<Building2 className="h-4 w-4" />}>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <Row label="Pending approval" value={Number(m.pending_approval ?? 0)} />
        <Row label="Active" value={Number(m.active ?? 0)} />
        <Row label="Contracts expiring" value={Number(m.contracts_expiring ?? 0)} />
      </div>
      {topRev.length > 0 && (
        <div className="mt-3">
          <p className="mb-1 text-xs font-medium text-muted">Top by revenue</p>
          <ul className="space-y-1 text-xs">
            {topRev.slice(0, 3).map((r, i) => (
              <li key={`rev-${r.id ?? r.name ?? "m"}-${i}`} className="flex justify-between">
                <span className="truncate">{r.name}</span>
                <span className="font-medium">{formatCents(Number(r.revenue_cents ?? 0))}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {topOrders.length > 0 && (
        <div className="mt-2">
          <p className="mb-1 text-xs font-medium text-muted">Top by orders</p>
          <ul className="space-y-1 text-xs">
            {topOrders.slice(0, 3).map((r, i) => (
              <li key={`ord-${r.id ?? r.name ?? "m"}-${i}`} className="flex justify-between">
                <span className="truncate">{r.name}</span>
                <span className="font-medium">{r.orders ?? 0}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      <Link href="/merchants" className="mt-2 inline-block text-sm text-secondary hover:underline">
        Merchants →
      </Link>
    </Panel>
  );
}

function DriversPanel({ center }: { center: DashboardCenter }) {
  const d = center.drivers as Record<string, number>;
  return (
    <Panel title="Drivers" icon={<Truck className="h-4 w-4" />}>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <Row label="Active assignments" value={Number(d.active_assignments ?? 0)} />
      </div>
      <p className="mt-2 text-xs text-muted">Live GPS is the driver pin PorterChain stores.</p>
      <Link href="/drivers" className="mt-2 inline-block text-sm text-secondary hover:underline">
        Drivers →
      </Link>
    </Panel>
  );
}

function FleetPanel({ center }: { center: DashboardCenter }) {
  const f = center.fleet;
  return (
    <Panel title="Fleet" icon={<Truck className="h-4 w-4" />}>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <Row label="Total vehicles" value={Number(f.vehicles_total ?? 0)} />
        <Row label="Active" value={Number(f.vehicles_active ?? 0)} />
        <Row label="Available" value={Number(f.vehicles_available ?? 0)} />
        <Row label="Utilization" value={`${f.utilization_percent ?? 0}%`} />
      </div>
    </Panel>
  );
}

function SystemHealthPanel({ health }: { health: Record<string, unknown> }) {
  const items: Array<{ key: string; label: string; val: unknown }> =
    INTEGRATION_HEALTH_CORE_KEYS.filter((k) => k in health).map((key) => ({
      key,
      label: INTEGRATION_HEALTH_LABELS[key] ?? key,
      val: health[key],
    }));
  for (const [key, val] of Object.entries(health)) {
    if (key === "routing") continue;
    if ((INTEGRATION_HEALTH_CORE_KEYS as readonly string[]).includes(key)) continue;
    if (val && typeof val === "object" && "status" in (val as object)) {
      items.push({ key, label: INTEGRATION_HEALTH_LABELS[key] ?? key, val });
    }
  }
  return (
    <Panel title="Health" icon={<CheckCircle2 className="h-4 w-4" />}>
      <div className="flex flex-wrap gap-2">
        {items.map(({ key, label, val }) => {
          const status = healthStatus(val);
          return (
            <span
              key={key}
              className={cn(
                "rounded-full px-2.5 py-1 text-xs font-medium",
                status === "healthy" && "bg-green-50 text-green-700",
                status === "warning" && "bg-amber-50 text-amber-800",
                status === "critical" && "bg-red-50 text-red-700",
                status === "unknown" && "bg-gray-100 text-muted"
              )}
            >
              {label}
            </span>
          );
        })}
      </div>
      <Link href="/system" className="mt-2 inline-block text-sm text-secondary hover:underline">
        System →
      </Link>
    </Panel>
  );
}

function RightSidebar({ center }: { center: DashboardCenter }) {
  const p = center.pending;
  return (
    <>
      <Panel title="Today's schedule" icon={<Calendar className="h-4 w-4" />}>
        <p className="text-sm text-muted">Use merchant and driver pages for follow-ups.</p>
      </Panel>
      <Panel title="Approvals & pending" icon={<Bell className="h-4 w-4" />}>
        <ul className="space-y-2 text-sm">
          <PendingRow label="Merchant approvals" count={p.merchant_approvals} href="/merchants" />
          <PendingRow label="Open claims" count={p.claims_open} href="/claims" />
          <PendingRow label="Support tickets" count={p.support_open} href="/support" />
          <PendingRow label="Quotes" count={p.quotes} href="/booking-drafts" />
          <PendingRow label="Contracts" count={p.contracts ?? 0} href="/leads" />
          <PendingRow label="Overdue CRM tasks" count={p.overdue_tasks ?? 0} href="/leads" />
        </ul>
      </Panel>
      <Panel title="Notifications" icon={<Bell className="h-4 w-4" />}>
        <p className="text-sm text-muted">
          Notifications poll the API (WebSocket when connected). Live map GPS is not a browser Open
          Operations for the dispatch feed.
        </p>
        <Link
          href="/operations"
          className="mt-2 inline-block text-sm text-secondary hover:underline"
        >
          Operations →
        </Link>
      </Panel>
    </>
  );
}

function WidgetLayoutPanel({
  widgets,
  onToggle,
  onClose,
}: {
  widgets: Record<WidgetId, boolean>;
  onToggle: (id: WidgetId) => void;
  onClose: () => void;
}) {
  return (
    <div className="rounded-xl border border-primary/10 bg-white p-4">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="font-semibold">Customize layout</h3>
        <button type="button" className="text-sm text-muted" onClick={onClose}>
          Close
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        {DASHBOARD_WIDGETS.map((w) => (
          <button
            key={w.id}
            type="button"
            onClick={() => onToggle(w.id)}
            className={cn(
              "rounded-lg border px-3 py-1.5 text-xs font-medium",
              widgets[w.id]
                ? "border-secondary bg-secondary/10 text-secondary"
                : "border-primary/10 text-muted"
            )}
          >
            {w.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between border-b border-primary/5 py-1">
      <span className="text-muted">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

function PendingRow({ label, count, href }: { label: string; count: number; href: string }) {
  return (
    <li className="flex justify-between">
      <Link href={href} className="text-secondary hover:underline">
        {label}
      </Link>
      <span className={cn("font-semibold", count > 0 && "text-amber-700")}>{count}</span>
    </li>
  );
}
