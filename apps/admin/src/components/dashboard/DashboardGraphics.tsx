"use client";

import { useMemo } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  Building2,
  LifeBuoy,
  Package,
  Sparkles,
  TrendingUp,
  Users,
  Wallet,
  Zap,
} from "lucide-react";
import { formatCents } from "@porterchain/ui/utils";
import ReportChart, {
  compactTrendOption,
  donutChartOption,
  funnelChartOption,
  horizontalBarOption,
  roseChartOption,
} from "@/components/reports/ReportChart";
import type { DashboardCenter } from "@/lib/dashboard";
import {
  AnimatedRing,
  BentoCell,
  BentoGrid,
  NumberTicker,
  SpotlightCard,
} from "@/components/dashboard/magic";
import { OpsPressureCard } from "@/components/dashboard/OpsPressureCard";

const fade = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0 },
};

function SpotlightHero({
  revenueToday,
  ordersToday,
  forecast,
  growthPercent,
  summary,
  anomalies,
  sla,
  util,
  health,
  alerts,
}: {
  revenueToday: number;
  ordersToday: number;
  forecast: number;
  growthPercent: number;
  summary: string | null;
  anomalies: string[];
  sla: number;
  util: number;
  health: number;
  alerts: number;
}) {
  return (
    <SpotlightCard className="bg-gradient-to-br from-white via-white to-sky-50/80 p-4 sm:p-5">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-1.5 text-xs font-medium text-muted">
            <Zap className="h-3.5 w-3.5 shrink-0 text-secondary" /> Today&apos;s capacity
          </p>
          <p className="mt-2 text-3xl font-bold tracking-tight text-primary sm:text-4xl">
            <NumberTicker value={Math.round(revenueToday / 100)} prefix="$" />
          </p>
          <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
            <span>
              <NumberTicker value={ordersToday} /> orders
            </span>
            <span>forecast {formatCents(forecast)}</span>
            <span
              className={
                growthPercent >= 0 ? "font-medium text-emerald-700" : "font-medium text-amber-700"
              }
            >
              {growthPercent >= 0 ? "+" : ""}
              {growthPercent}% trend
            </span>
          </p>
          {summary ? (
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-primary/80">{summary}</p>
          ) : null}
          {anomalies.length > 0 ? (
            <ul className="mt-2 space-y-1 text-xs text-muted">
              {anomalies.slice(0, 3).map((a, i) => (
                <li key={`anom-${i}`}>• {a}</li>
              ))}
            </ul>
          ) : null}
          <div className="mt-3 flex flex-wrap gap-3">
            <Link
              href="/operations?view=tools&tool=ai"
              className="inline-flex items-center gap-1 text-xs font-medium text-secondary hover:underline"
            >
              <Sparkles className="h-3.5 w-3.5" /> Copilot
            </Link>
            <Link href="/operations?view=attention" className="text-xs text-muted hover:underline">
              Attention →
            </Link>
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap justify-start gap-3 sm:gap-5 lg:justify-end">
          <AnimatedRing value={sla} label="SLA" size={168} />
          <AnimatedRing value={util} label="Utilization" size={168} />
          <AnimatedRing value={health} label="Fleet health" size={168} />
        </div>
      </div>
      {alerts > 0 && (
        <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          {alerts} live alert{alerts === 1 ? "" : "s"} — open Attention or Copilot.
        </p>
      )}
    </SpotlightCard>
  );
}

function CareMeters({
  supportOpen,
  supportUrgent,
  claimsOpen,
  claimsInvestigating,
}: {
  supportOpen: number;
  supportUrgent: number;
  claimsOpen: number;
  claimsInvestigating: number;
}) {
  const rows = [
    {
      label: "Support open",
      value: supportOpen,
      scale: Math.max(10, supportOpen),
      href: "/support",
      tone: supportUrgent > 0 ? "danger" : supportOpen > 5 ? "warn" : "ok",
    },
    {
      label: "Support urgent",
      value: supportUrgent,
      scale: Math.max(5, supportUrgent),
      href: "/support",
      tone: supportUrgent > 0 ? "danger" : "ok",
    },
    {
      label: "Claims open",
      value: claimsOpen,
      scale: Math.max(8, claimsOpen),
      href: "/claims",
      tone: claimsOpen >= 5 ? "danger" : claimsOpen > 0 ? "warn" : "ok",
    },
    {
      label: "Investigating",
      value: claimsInvestigating,
      scale: Math.max(5, claimsInvestigating),
      href: "/claims",
      tone: claimsInvestigating > 0 ? "warn" : "ok",
    },
  ] as const;
  const bar: Record<string, string> = {
    ok: "bg-emerald-500",
    warn: "bg-amber-500",
    danger: "bg-red-500",
  };
  const track: Record<string, string> = {
    ok: "bg-emerald-100",
    warn: "bg-amber-100",
    danger: "bg-red-100",
  };

  return (
    <ul className="space-y-2.5">
      {rows.map((r) => (
        <li key={r.label}>
          <Link href={r.href} className="group block">
            <div className="mb-0.5 flex justify-between text-xs">
              <span className="text-muted group-hover:text-primary">{r.label}</span>
              <span className="font-semibold tabular-nums text-primary">{r.value}</span>
            </div>
            <div className={`h-1.5 overflow-hidden rounded-full ${track[r.tone]}`}>
              <motion.div
                className={`h-full rounded-full ${bar[r.tone]}`}
                initial={{ width: 0 }}
                animate={{
                  width: `${Math.min(100, (r.value / Math.max(r.scale, 1)) * 100)}%`,
                }}
                transition={{ duration: 0.55, ease: "easeOut" }}
              />
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}

/**
 * High-graphics intelligence canvas — Magic UI bento + ECharts charts.
 */
export default function DashboardGraphics({
  center,
  operations,
}: {
  center: DashboardCenter;
  operations: Record<string, unknown>;
}) {
  const orderDonut = useMemo(() => {
    const o = center.orders;
    const slices = [
      { name: "Waiting", value: Number(o.waiting_dispatch ?? 0) },
      { name: "Assigned", value: Number(o.assigned ?? 0) },
      { name: "In transit", value: Number(o.orders_in_progress ?? 0) },
      { name: "Delivered", value: Number(o.delivered ?? 0) },
      { name: "Failed", value: Number(o.failed ?? 0) },
    ];
    const total = slices.reduce((s, x) => s + x.value, 0);
    return donutChartOption(total > 0 ? slices : [{ name: "No orders", value: 1 }], {
      centerLabel: total > 0 ? "Orders" : "Empty",
    });
  }, [center.orders]);

  const financeDonut = useMemo(() => {
    const f = center.finance;
    const slices = [
      { name: "Today", value: Number(f.today_revenue_cents ?? 0) },
      { name: "Outstanding", value: Number(f.outstanding_invoices_cents ?? 0) },
      { name: "Paid MTD", value: Number(f.paid_invoices_cents ?? 0) },
      { name: "Payouts due", value: Number(f.driver_payouts_pending_cents ?? 0) },
    ].filter((s) => s.value > 0);
    return donutChartOption(slices.length ? slices : [{ name: "No finance data", value: 1 }], {
      centerLabel: "Cash",
    });
  }, [center.finance]);

  const bookingFunnel = useMemo(() => {
    const b = center.booking;
    return funnelChartOption([
      { name: "Drafts", value: Number(b.total_drafts ?? b.active_drafts ?? 0) },
      { name: "Active", value: Number(b.active_drafts ?? 0) },
      { name: "Confirmed", value: Number(b.confirmed_drafts ?? 0) },
      { name: "Abandoned", value: Number(b.abandoned_now ?? 0) },
    ]);
  }, [center.booking]);

  const merchantBars = useMemo(() => {
    const top =
      (center.merchants.top_by_revenue as Array<{
        name?: string;
        revenue_cents?: number;
      }>) ?? [];
    const rows = top
      .filter((m) => m.name)
      .slice(0, 5)
      .map((m) => ({ name: String(m.name), value: Number(m.revenue_cents ?? 0) }));
    return horizontalBarOption(rows, { valueLabel: "cents" });
  }, [center.merchants]);

  const trendChart = useMemo(() => {
    const t = center.trends;
    if (!t?.labels?.length) return null;
    return compactTrendOption(
      t.labels,
      t.revenue_cents.map((c) => Math.round(c / 100)),
      t.orders
    );
  }, [center.trends]);

  const crmRose = useMemo(() => {
    const c = center.crm;
    const slices = [
      { name: "New leads", value: Number(c.new_leads ?? 0) },
      { name: "Follow-ups", value: Number(c.todays_follow_ups ?? 0) },
      { name: "Meetings", value: Number(c.meetings_today ?? 0) },
      { name: "Open deals", value: Number(c.open_deals ?? 0) },
      { name: "Won MTD", value: Number(c.won_deals_this_month ?? 0) },
    ].filter((s) => s.value > 0);
    return roseChartOption(
      slices.length ? slices : [{ name: "No CRM activity", value: 1 }],
      "CRM pulse"
    );
  }, [center.crm]);

  const revenueToday = Number(
    center.kpis.revenue_today_cents ?? center.kpis.todays_revenue_cents ?? 0
  );
  const ordersToday = Number(center.kpis.orders_today ?? center.kpis.todays_bookings ?? 0);
  const sla = Number(center.executive.delivery_sla_percent ?? 100);
  const util = Number(center.fleet.utilization_percent ?? 0);
  const health = Number(center.kpis.fleet_health_percent ?? 100);
  const alerts = Number(center.smart.alerts ?? operations.open_exceptions ?? 0);
  const growthPercent = Number(center.executive.growth_percent ?? 0);
  const anomalies = Array.isArray(center.smart.anomalies)
    ? (center.smart.anomalies as string[])
    : [];
  const conversion = Number(center.booking.conversion_rate_percent ?? 0);
  const paymentSuccess = Number(center.finance.payment_success_rate ?? 100);

  return (
    <motion.section
      className="space-y-3"
      initial={false}
      animate="show"
      variants={{
        hidden: {},
        show: { transition: { staggerChildren: 0.04 } },
      }}
    >
      <div className="flex items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-secondary">
            Intelligence canvas
          </p>
          <h2 className="text-lg font-bold text-primary">Network at a glance</h2>
        </div>
        <p className="text-xs text-muted">Live KPIs · charts refresh with command center</p>
      </div>

      <BentoGrid>
        <motion.div variants={fade} className="md:col-span-2 xl:col-span-4">
          <SpotlightHero
            revenueToday={revenueToday}
            ordersToday={ordersToday}
            forecast={Number(center.executive.forecast_revenue_cents ?? 0)}
            growthPercent={growthPercent}
            summary={center.smart.ai_summary ? String(center.smart.ai_summary) : null}
            anomalies={anomalies}
            sla={sla}
            util={util}
            health={health}
            alerts={alerts}
          />
        </motion.div>

        <motion.div variants={fade}>
          <BentoCell>
            <p className="mb-1 flex items-center gap-1.5 text-xs font-medium text-muted">
              <Package className="h-3.5 w-3.5 text-secondary" /> Order mix
            </p>
            <ReportChart option={orderDonut} height={200} />
          </BentoCell>
        </motion.div>

        <motion.div variants={fade}>
          <BentoCell>
            <p className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted">
              <Activity className="h-3.5 w-3.5 text-secondary" /> Ops pressure
            </p>
            <OpsPressureCard operations={operations} />
          </BentoCell>
        </motion.div>

        <motion.div variants={fade}>
          <BentoCell>
            <p className="mb-1 flex items-center gap-1.5 text-xs font-medium text-muted">
              <Wallet className="h-3.5 w-3.5 text-secondary" /> Cash position
            </p>
            <ReportChart option={financeDonut} height={200} />
            <p className="mt-1 text-center text-[11px] text-muted">
              Pay success {paymentSuccess}% · profit{" "}
              {formatCents(Number(center.finance.profit_estimate_cents ?? 0))}
            </p>
          </BentoCell>
        </motion.div>

        <motion.div variants={fade}>
          <BentoCell>
            <p className="mb-1 flex items-center gap-1.5 text-xs font-medium text-muted">
              <TrendingUp className="h-3.5 w-3.5 text-secondary" /> Booking funnel
            </p>
            <ReportChart option={bookingFunnel} height={200} />
            <p className="mt-1 text-center text-[11px] text-muted">Conversion {conversion}%</p>
          </BentoCell>
        </motion.div>

        {trendChart && (
          <motion.div variants={fade} className="md:col-span-2 xl:col-span-2">
            <BentoCell>
              <p className="mb-1 flex items-center gap-1.5 text-xs font-medium text-muted">
                <TrendingUp className="h-3.5 w-3.5 text-secondary" /> 7-day revenue & orders
              </p>
              <ReportChart option={trendChart} height={220} />
            </BentoCell>
          </motion.div>
        )}

        <motion.div variants={fade} className="md:col-span-2 xl:col-span-2">
          <BentoCell>
            <p className="mb-1 flex items-center gap-1.5 text-xs font-medium text-muted">
              <Building2 className="h-3.5 w-3.5 text-secondary" /> Top merchants (revenue)
            </p>
            <ReportChart option={merchantBars} height={220} />
            <Link
              href="/merchants"
              className="mt-1 inline-block text-xs text-secondary hover:underline"
            >
              Merchants →
            </Link>
          </BentoCell>
        </motion.div>

        <motion.div variants={fade} className="md:col-span-2">
          <BentoCell>
            <p className="mb-1 flex items-center gap-1.5 text-xs font-medium text-muted">
              <Users className="h-3.5 w-3.5 text-secondary" /> CRM rose
            </p>
            <ReportChart option={crmRose} height={220} />
          </BentoCell>
        </motion.div>

        <motion.div variants={fade}>
          <BentoCell>
            <p className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted">
              <LifeBuoy className="h-3.5 w-3.5 text-secondary" /> Care load
            </p>
            <CareMeters
              supportOpen={Number(center.support.open_tickets ?? 0)}
              supportUrgent={Number(center.support.urgent_tickets ?? 0)}
              claimsOpen={Number(center.claims.open_claims ?? 0)}
              claimsInvestigating={Number(center.claims.under_investigation ?? 0)}
            />
          </BentoCell>
        </motion.div>

        <motion.div variants={fade}>
          <BentoCell className="flex min-h-[140px] flex-col justify-between gap-2">
            <p className="flex items-center gap-1.5 text-xs font-medium text-muted">
              <AlertTriangle className="h-3.5 w-3.5 text-secondary" /> Exceptions
            </p>
            <NumberTicker
              value={Number(operations.open_exceptions ?? 0)}
              className="text-4xl font-bold text-primary"
            />
            <Link
              href="/operations?view=attention"
              className="text-xs text-secondary hover:underline"
            >
              Clear attention →
            </Link>
          </BentoCell>
        </motion.div>

        <motion.div variants={fade}>
          <BentoCell className="flex min-h-[140px] flex-col justify-between gap-2">
            <p className="text-xs font-medium text-muted">Pipeline value</p>
            <p className="text-2xl font-bold text-primary">
              {formatCents(Number(center.crm.pipeline_value_cents ?? 0))}
            </p>
            <Link href="/leads" className="text-xs text-secondary hover:underline">
              Open CRM →
            </Link>
          </BentoCell>
        </motion.div>

        <motion.div variants={fade}>
          <BentoCell className="flex min-h-[140px] flex-col justify-between gap-2">
            <p className="text-xs font-medium text-muted">Fleet active</p>
            <NumberTicker
              value={Number(center.fleet.vehicles_active ?? 0)}
              className="text-4xl font-bold text-primary"
            />
            <p className="text-xs text-muted">
              of {Number(center.fleet.vehicles_total ?? 0)} · util {util}%
            </p>
          </BentoCell>
        </motion.div>
      </BentoGrid>
    </motion.section>
  );
}
