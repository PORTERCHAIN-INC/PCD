"use client";

import type { DashboardChartPoint } from "@/lib/api";
import ReportChart, { areaTrendOption, barChartOption } from "@/components/charts/ReportChart";
import { SpotlightCard } from "@/components/dashboard/magic";

interface PerformanceChartProps {
  title: string;
  subtitle: string;
  series: DashboardChartPoint[];
  mode?: "area" | "bar";
  dollars?: boolean;
}

export function PerformanceChart({
  title,
  subtitle,
  series,
  mode = "area",
  dollars = false,
}: PerformanceChartProps) {
  const labels = series.map((p) => p.label);
  const values = series.map((p) => p.value);
  const option =
    mode === "bar"
      ? barChartOption(labels, values, { dollars })
      : areaTrendOption(labels, values, {
          name: title,
          dollars,
          color: dollars ? "#0ea5e9" : "#2563eb",
        });

  return (
    <SpotlightCard className="p-6">
      <div className="mb-2">
        <h2 className="text-lg font-semibold text-primary">{title}</h2>
        <p className="text-sm text-muted">{subtitle}</p>
      </div>
      <ReportChart option={option} height={200} />
    </SpotlightCard>
  );
}

export function SpendPerformanceChart({ series }: { series: DashboardChartPoint[] }) {
  return (
    <PerformanceChart
      title="Daily Spend"
      subtitle="Last 7 days — operational spend"
      series={series}
      mode="bar"
      dollars
    />
  );
}

export function OrdersPerformanceChart({ series }: { series: DashboardChartPoint[] }) {
  return (
    <PerformanceChart
      title="Daily Orders"
      subtitle="Last 7 days — shipment volume"
      series={series}
      mode="area"
    />
  );
}
