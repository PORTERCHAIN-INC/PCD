"use client";

import {
  OrdersPerformanceChart,
  PerformanceChart,
  SpendPerformanceChart,
} from "@/components/dashboard/PerformanceChart";
import { formatPercent, type ExecutiveReport } from "@/lib/reports";
import { formatCents } from "@/lib/utils";
import { SpendAttribution } from "./Spend";
import { KpiGrid, Metric, RankedList } from "./shared";

export function ExecutiveTab({ data }: { data: ExecutiveReport }) {
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
