import type { DashboardChartPoint } from "@/lib/api";
import { formatCents } from "@/lib/utils";

interface PerformanceChartProps {
  title: string;
  subtitle: string;
  series: DashboardChartPoint[];
  formatValue?: (value: number) => string;
}

export function PerformanceChart({ title, subtitle, series, formatValue }: PerformanceChartProps) {
  const max = Math.max(...series.map((p) => p.value), 1);
  const fmt = formatValue ?? ((v: number) => String(v));

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-6">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-primary">{title}</h2>
        <p className="text-sm text-muted">{subtitle}</p>
      </div>
      <div className="flex h-40 items-end gap-2">
        {series.map((point, i) => (
          <div key={`${point.label}-${i}`} className="flex flex-1 flex-col items-center gap-2">
            <span className="text-[10px] font-medium text-muted">{fmt(point.value)}</span>
            <div
              className="w-full rounded-t-md bg-secondary/80 transition-all"
              style={{ height: `${Math.max(8, (point.value / max) * 100)}%` }}
              title={`${point.label}: ${fmt(point.value)}`}
            />
            <span className="text-xs text-muted">{point.label}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

export function SpendPerformanceChart({ series }: { series: DashboardChartPoint[] }) {
  return (
    <PerformanceChart
      title="Daily Spend"
      subtitle="Last 7 days — operational spend"
      series={series}
      formatValue={(v) => formatCents(v)}
    />
  );
}

export function OrdersPerformanceChart({ series }: { series: DashboardChartPoint[] }) {
  return (
    <PerformanceChart
      title="Daily Orders"
      subtitle="Last 7 days — shipment volume"
      series={series}
    />
  );
}
