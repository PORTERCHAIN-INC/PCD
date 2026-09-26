"use client";

import { useMemo, type ComponentType } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Activity,
  Package,
  Truck,
  Wallet,
  AlertTriangle,
  FileText,
  LifeBuoy,
  Zap,
} from "lucide-react";
import ReportChart, {
  areaTrendOption,
  barChartOption,
  compactTrendOption,
  donutChartOption,
  funnelChartOption,
  roseChartOption,
  sparklineOption,
} from "@/components/charts/ReportChart";
import {
  AnimatedRing,
  BentoCell,
  BentoGrid,
  NumberTicker,
  SpotlightCard,
} from "@/components/dashboard/magic";
import type { MerchantDashboard } from "@/lib/api";
import type { MerchantPortalJob } from "@/lib/merchant-nav";
import { formatCents } from "@/lib/utils";

const fade = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0 },
};

function humanState(state: string): string {
  return state.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function KpiTile({
  label,
  value,
  hint,
  href,
  spark,
  prefix = "",
  suffix = "",
  icon: Icon,
}: {
  label: string;
  value: number;
  hint?: string;
  href?: string;
  spark?: number[];
  prefix?: string;
  suffix?: string;
  icon?: ComponentType<{ className?: string }>;
}) {
  const body = (
    <div className="flex h-full flex-col gap-2 p-4">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-medium text-muted">{label}</p>
        {Icon ? <Icon className="h-3.5 w-3.5 shrink-0 text-secondary" /> : null}
      </div>
      <p className="text-2xl font-bold tracking-tight text-primary">
        <NumberTicker value={value} prefix={prefix} suffix={suffix} />
      </p>
      {hint ? <p className="text-[11px] text-muted">{hint}</p> : null}
      {spark && spark.length > 1 ? (
        <ReportChart option={sparklineOption(spark)} height={36} compact className="mt-auto" />
      ) : null}
    </div>
  );

  if (href) {
    return (
      <SpotlightCard className="transition hover:border-secondary/30">
        <Link href={href} className="block h-full">
          {body}
        </Link>
      </SpotlightCard>
    );
  }
  return <SpotlightCard>{body}</SpotlightCard>;
}

function PersonaHero({ job, data }: { job: MerchantPortalJob; data: MerchantDashboard }) {
  if (job === "accounting") {
    return (
      <SpotlightCard className="bg-gradient-to-br from-white via-white to-sky-50/80 p-4 sm:p-5">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 flex-1">
            <p className="flex items-center gap-1.5 text-xs font-medium text-muted">
              <Wallet className="h-3.5 w-3.5 shrink-0 text-secondary" /> Outstanding this period
            </p>
            <p className="mt-2 text-3xl font-bold tracking-tight text-primary sm:text-4xl">
              <NumberTicker value={Math.round(data.outstanding_balance_cents / 100)} prefix="$" />
            </p>
            <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
              <span>
                Monthly spend{" "}
                <span className="font-medium text-primary">
                  {formatCents(data.monthly_spend_cents)}
                </span>
              </span>
              <span>
                <NumberTicker value={data.invoices_due} /> invoice
                {data.invoices_due === 1 ? "" : "s"} due
              </span>
              {data.payment_terms ? (
                <span className="capitalize">{data.payment_terms.replaceAll("_", " ")}</span>
              ) : null}
            </p>
            <div className="mt-3 flex flex-wrap gap-3">
              <Link href="/billing" className="text-xs font-medium text-secondary hover:underline">
                Billing →
              </Link>
              <Link href="/invoices" className="text-xs text-muted hover:underline">
                Invoices →
              </Link>
            </div>
          </div>
          <div className="flex shrink-0 flex-wrap justify-start gap-3 lg:justify-end">
            <AnimatedRing
              value={Math.min(100, data.invoices_due * 20)}
              label="Invoice pressure"
              mode="pressure"
              size={108}
            />
          </div>
        </div>
      </SpotlightCard>
    );
  }

  if (job === "viewer") {
    return (
      <SpotlightCard className="bg-gradient-to-br from-white via-white to-sky-50/80 p-4 sm:p-5">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 flex-1">
            <p className="flex items-center gap-1.5 text-xs font-medium text-muted">
              <Truck className="h-3.5 w-3.5 shrink-0 text-secondary" /> Shipments in transit
            </p>
            <p className="mt-2 text-3xl font-bold tracking-tight text-primary sm:text-4xl">
              <NumberTicker value={data.in_transit} />
            </p>
            <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
              <span>
                <NumberTicker value={data.todays_orders} /> booked today
              </span>
              <span>
                <NumberTicker value={data.delivered_today} /> delivered today
              </span>
            </p>
            <Link
              href="/tracking"
              className="mt-3 inline-block text-xs font-medium text-secondary hover:underline"
            >
              Live tracking →
            </Link>
          </div>
          <AnimatedRing
            value={
              data.todays_orders > 0
                ? Math.round((data.delivered_today / Math.max(data.todays_orders, 1)) * 100)
                : data.delivered_today > 0
                  ? 100
                  : 0
            }
            label="Delivered today"
            size={108}
          />
        </div>
      </SpotlightCard>
    );
  }

  // dispatcher + owner
  const onTime = data.on_time_percent ?? 0;
  const success = data.delivery_success_percent ?? 0;
  return (
    <SpotlightCard className="bg-gradient-to-br from-white via-white to-sky-50/80 p-4 sm:p-5">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-1.5 text-xs font-medium text-muted">
            <Zap className="h-3.5 w-3.5 shrink-0 text-secondary" />
            {job === "owner" ? "Network pulse today" : "Dispatch pulse today"}
          </p>
          <p className="mt-2 text-3xl font-bold tracking-tight text-primary sm:text-4xl">
            <NumberTicker value={data.todays_orders} />
            <span className="ml-2 text-lg font-semibold text-muted">orders</span>
          </p>
          <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
            <span>
              <NumberTicker value={data.awaiting_pickup} /> awaiting pickup
            </span>
            <span>
              <NumberTicker value={data.in_transit} /> in transit
            </span>
            <span>
              <NumberTicker value={data.delivered_today} /> delivered
            </span>
            {job === "owner" ? (
              <span className="font-medium text-primary">
                {formatCents(data.monthly_spend_cents)} MTD
              </span>
            ) : null}
          </p>
          <div className="mt-3 flex flex-wrap gap-3">
            <Link href="/orders" className="text-xs font-medium text-secondary hover:underline">
              Orders →
            </Link>
            <Link href="/book" className="text-xs text-muted hover:underline">
              Request capacity →
            </Link>
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap justify-start gap-2 sm:gap-4 lg:justify-end">
          <AnimatedRing value={onTime} label="On-time" size={108} />
          <AnimatedRing value={success} label="Delivered of bookings" size={108} />
          {data.open_claims > 0 || data.open_support_tickets > 0 ? (
            <AnimatedRing
              value={Math.min(100, (data.open_claims + data.open_support_tickets) * 15)}
              label="Open issues"
              mode="pressure"
              size={108}
            />
          ) : null}
        </div>
      </div>
    </SpotlightCard>
  );
}

export function MerchantDashboardGraphics({
  data,
  job,
}: {
  data: MerchantDashboard;
  job: MerchantPortalJob;
}) {
  const showOps = job === "dispatcher" || job === "owner";
  const showFinance = job === "accounting" || job === "owner";
  const showTrack = job === "viewer" || showOps;

  const orderLabels = data.performance_charts.daily_orders.map((p) => p.label);
  const orderValues = data.performance_charts.daily_orders.map((p) => p.value);
  const spendLabels = data.performance_charts.daily_spend_cents.map((p) => p.label);
  const spendCents = data.performance_charts.daily_spend_cents.map((p) => p.value);
  const spendDollars = spendCents.map((c) => Math.round(c / 100));

  const stateSlices = useMemo(
    () =>
      data.performance_charts.orders_by_state.map((s) => ({
        name: humanState(s.state),
        value: s.count,
      })),
    [data.performance_charts.orders_by_state]
  );

  const stateTotal = stateSlices.reduce((a, s) => a + s.value, 0);

  const pipeline = useMemo(
    () => [
      { name: "Booked today", value: data.todays_orders },
      { name: "Awaiting pickup", value: data.awaiting_pickup },
      { name: "In transit", value: data.in_transit },
      { name: "Delivered today", value: data.delivered_today },
    ],
    [data.todays_orders, data.awaiting_pickup, data.in_transit, data.delivered_today]
  );

  const dualLabels = orderLabels.length >= spendLabels.length ? orderLabels : spendLabels;
  const dualOrders =
    orderValues.length === dualLabels.length
      ? orderValues
      : dualLabels.map((_, i) => orderValues[i] ?? 0);
  const dualSpend =
    spendDollars.length === dualLabels.length
      ? spendDollars
      : dualLabels.map((_, i) => spendDollars[i] ?? 0);

  return (
    <motion.div
      className="space-y-4"
      initial="hidden"
      animate="show"
      variants={{ show: { transition: { staggerChildren: 0.06 } } }}
    >
      <motion.div variants={fade}>
        <PersonaHero job={job} data={data} />
      </motion.div>

      <motion.div variants={fade}>
        <BentoGrid>
          {showTrack ? (
            <KpiTile
              label="Today's orders"
              value={data.todays_orders}
              spark={orderValues}
              href="/orders"
              icon={Package}
            />
          ) : null}
          {showOps ? (
            <KpiTile
              label="Awaiting pickup"
              value={data.awaiting_pickup}
              href="/orders"
              icon={Activity}
              hint="Ready for driver"
            />
          ) : null}
          {showTrack ? (
            <KpiTile label="In transit" value={data.in_transit} href="/tracking" icon={Truck} />
          ) : null}
          {showOps ? (
            <KpiTile label="Monthly orders" value={data.monthly_orders} icon={Package} />
          ) : null}
          {showFinance ? (
            <KpiTile
              label="Monthly spend"
              value={Math.round(data.monthly_spend_cents / 100)}
              prefix="$"
              spark={spendDollars}
              href="/billing"
              icon={Wallet}
            />
          ) : null}
          {showFinance ? (
            <KpiTile
              label="Outstanding"
              value={Math.round(data.outstanding_balance_cents / 100)}
              prefix="$"
              href="/invoices"
              icon={FileText}
              hint={`${data.invoices_due} due`}
            />
          ) : null}
          {showOps && data.open_claims > 0 ? (
            <KpiTile
              label="Open claims"
              value={data.open_claims}
              href="/claims"
              icon={AlertTriangle}
            />
          ) : null}
          {job !== "viewer" ? (
            <KpiTile
              label="Support tickets"
              value={data.open_support_tickets}
              href="/support"
              icon={LifeBuoy}
            />
          ) : null}
        </BentoGrid>
      </motion.div>

      <motion.div variants={fade} className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {showTrack ? (
          <SpotlightCard className="p-4 xl:col-span-1">
            <p className="text-sm font-semibold text-primary">Daily orders</p>
            <p className="mb-1 text-xs text-muted">Last 7 days — shipment volume</p>
            <ReportChart
              option={areaTrendOption(orderLabels, orderValues, {
                name: "Orders",
                color: "#2563eb",
              })}
              height={220}
            />
          </SpotlightCard>
        ) : null}

        {showFinance ? (
          <SpotlightCard className="p-4 xl:col-span-1">
            <p className="text-sm font-semibold text-primary">Daily spend</p>
            <p className="mb-1 text-xs text-muted">Last 7 days — operational spend</p>
            <ReportChart
              option={barChartOption(spendLabels, spendCents, {
                dollars: true,
                color: "#0ea5e9",
              })}
              height={220}
            />
          </SpotlightCard>
        ) : null}

        {showOps ? (
          <SpotlightCard className="p-4 xl:col-span-1">
            <p className="text-sm font-semibold text-primary">Today&apos;s pipeline</p>
            <p className="mb-1 text-xs text-muted">Booked → pickup → road → delivered</p>
            <ReportChart option={funnelChartOption(pipeline)} height={220} />
          </SpotlightCard>
        ) : null}

        {showTrack && stateSlices.length > 0 ? (
          <SpotlightCard className="p-4 xl:col-span-1">
            <p className="text-sm font-semibold text-primary">Orders by status</p>
            <p className="mb-1 text-xs text-muted">Active mix across your account</p>
            <ReportChart
              option={donutChartOption(stateSlices, {
                centerLabel: String(stateTotal),
              })}
              height={240}
            />
          </SpotlightCard>
        ) : null}

        {job === "owner" && dualLabels.length > 0 ? (
          <SpotlightCard className="p-4 lg:col-span-2 xl:col-span-2">
            <p className="text-sm font-semibold text-primary">Spend vs volume</p>
            <p className="mb-1 text-xs text-muted">
              Dual trend — capacity usage and what you&apos;re paying
            </p>
            <ReportChart
              option={compactTrendOption(dualLabels, dualSpend, dualOrders)}
              height={240}
            />
          </SpotlightCard>
        ) : null}

        {job === "accounting" && stateSlices.length > 0 ? (
          <SpotlightCard className="p-4">
            <p className="text-sm font-semibold text-primary">Status rose</p>
            <p className="mb-1 text-xs text-muted">Where volume sits across states</p>
            <ReportChart option={roseChartOption(stateSlices)} height={240} />
          </SpotlightCard>
        ) : null}

        {job === "viewer" && stateSlices.length > 0 ? (
          <SpotlightCard className="p-4">
            <p className="text-sm font-semibold text-primary">Status mix</p>
            <p className="mb-1 text-xs text-muted">Where your shipments are now</p>
            <ReportChart option={roseChartOption(stateSlices)} height={240} />
          </SpotlightCard>
        ) : null}
      </motion.div>
    </motion.div>
  );
}
